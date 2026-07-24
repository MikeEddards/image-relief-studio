from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageTk
import numpy as np

from relief_mesh import MeshSettings, build_mesh, export_mesh, prepare_heightmap


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class ReliefStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Image Relief Studio")
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.image_path = ""
        self.svg_path = ""
        self.mesh = None
        self.preview_photo = None
        self.preview_image = None
        self.preview_zoom = 1.0
        self._preview_job = None
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        controls = ctk.CTkScrollableFrame(self, width=340, label_text="Model controls")
        controls.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        preview = ctk.CTkFrame(self)
        preview.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        preview.grid_rowconfigure(1, weight=1)
        preview.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(controls, text="Open image", command=self.open_image).pack(fill="x", pady=(4, 8))
        self.file_label = ctk.CTkLabel(controls, text="No image selected", wraplength=300)
        self.file_label.pack(fill="x", pady=(0, 12))

        self.mode = self._option(controls, "Relief mode", ["Brightness", "Flat"], "Brightness")
        self.offset = self._slider(controls, "Design offset (mm)", -8, 8, 2.0, 0.1)
        self.base_on = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(controls, text="Include baseplate", variable=self.base_on,
                        command=self.queue_preview).pack(anchor="w", pady=8)
        self.shape = self._option(controls, "Baseplate shape",
                                  ["Rectangle", "Rounded rectangle", "Ellipse", "SVG"],
                                  "Rounded rectangle", self.shape_changed)
        self.svg_button = ctk.CTkButton(controls, text="Choose baseplate SVG", command=self.open_svg)
        self.svg_button.pack(fill="x", pady=(0, 8))
        self.width = self._slider(controls, "Model width (mm)", 20, 250, 80, 1)
        self.base = self._slider(controls, "Base thickness (mm)", 0.4, 12, 2, 0.1)
        self.resolution = self._slider(controls, "Mesh resolution (max side)", 50, 1600, 600, 25)
        self.threshold = self._slider(controls, "Flat-mode threshold", 0, 1, 0.5, 0.01)
        self.response = self._slider(controls, "Brightness response", 0.2, 3, 1, 0.05)
        self.smoothing = self._slider(controls, "Smoothing (pixels)", 0, 6, 1, 0.1)
        self.invert = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(controls, text="Invert image", variable=self.invert,
                        command=self.queue_preview).pack(anchor="w", pady=8)

        ctk.CTkLabel(controls, text="Surface fitting",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(14, 4))
        self.curve_on = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(controls, text="Fit model to curved surface", variable=self.curve_on,
                        command=self.queue_preview).pack(anchor="w", pady=8)
        self.curve_profile = self._option(
            controls, "Curve profile",
            ["Cylinder", "Flat center + curved sides"], "Cylinder"
        )
        self.curve_radius = self._slider(controls, "Cylinder radius (mm)", 10, 500, 75, 1)
        self.flat_center = self._slider(controls, "Flat center width (mm)", 5, 400, 50, 1)
        self.side_radius = self._slider(controls, "Side radius (mm)", 5, 250, 15, 1)
        self.side_wrap = self._slider(controls, "Side wrap angle (degrees)", 0, 180, 90, 1)
        self.curve_axis = self._option(controls, "Bend across",
                                       ["Horizontal", "Vertical"], "Horizontal")
        self.curve_side = self._option(controls, "Curve side",
                                       ["Convex", "Concave"], "Convex")

        ctk.CTkLabel(preview, text="Shaded relief preview", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, pady=(14, 4))
        canvas_frame = ctk.CTkFrame(preview)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=8)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.preview_canvas = tk.Canvas(canvas_frame, bg="#17191c", highlightthickness=0,
                                        cursor="fleur")
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        self.preview_canvas.create_text(360, 260, text="Open an image to begin",
                                        fill="#b7b7b7", tags="placeholder")
        self.preview_canvas.bind("<MouseWheel>", self._mouse_zoom)
        self.preview_canvas.bind("<ButtonPress-1>", lambda e: self.preview_canvas.scan_mark(e.x, e.y))
        self.preview_canvas.bind("<B1-Motion>", lambda e: self.preview_canvas.scan_dragto(e.x, e.y, gain=1))

        view_actions = ctk.CTkFrame(preview, fg_color="transparent")
        view_actions.grid(row=2, column=0, pady=(0, 4))
        ctk.CTkButton(view_actions, text="−", width=42, command=lambda: self.zoom_preview(0.8)).pack(side="left", padx=3)
        ctk.CTkButton(view_actions, text="Fit", width=64, command=self.fit_preview).pack(side="left", padx=3)
        ctk.CTkButton(view_actions, text="+", width=42, command=lambda: self.zoom_preview(1.25)).pack(side="left", padx=3)
        ctk.CTkLabel(view_actions, text="Mouse wheel: zoom  •  Drag: pan").pack(side="left", padx=10)
        actions = ctk.CTkFrame(preview, fg_color="transparent")
        actions.grid(row=3, column=0, pady=(0, 10))
        self.generate_button = ctk.CTkButton(actions, text="Generate 3D mesh", command=self.generate_mesh)
        self.generate_button.pack(side="left", padx=6)
        self.viewer_button = ctk.CTkButton(actions, text="Open 3D Preview", command=self.show_3d_preview)
        self.viewer_button.pack(side="left", padx=6)
        self.export_stl = ctk.CTkButton(actions, text="Export STL", command=lambda: self.export(".stl"))
        self.export_stl.pack(side="left", padx=6)
        self.export_3mf = ctk.CTkButton(actions, text="Export 3MF", command=lambda: self.export(".3mf"))
        self.export_3mf.pack(side="left", padx=6)
        self.status = ctk.CTkLabel(preview, text="Ready")
        self.status.grid(row=4, column=0, pady=(0, 10))

    def _option(self, parent, label, values, default, command=None):
        ctk.CTkLabel(parent, text=label).pack(anchor="w")
        var = ctk.StringVar(value=default)
        ctk.CTkOptionMenu(parent, values=values, variable=var,
                          command=command or (lambda _: self.queue_preview())).pack(fill="x", pady=(2, 10))
        return var

    def _slider(self, parent, label, start, end, initial, step):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(2, 8))
        text = ctk.StringVar()
        ctk.CTkLabel(row, text=label).pack(side="left")
        ctk.CTkLabel(row, textvariable=text, width=58).pack(side="right")
        steps = max(1, round((end - start) / step))
        slider = ctk.CTkSlider(parent, from_=start, to=end, number_of_steps=steps)
        slider.set(initial)
        slider.pack(fill="x", pady=(0, 8))
        slider._display_var = text
        slider._display_step = step
        slider.configure(command=lambda value, s=slider: self._slider_changed(s, value))
        self._slider_changed(slider, initial, update=False)
        return slider

    def _slider_changed(self, slider, value, update=True):
        digits = 0 if slider._display_step >= 1 else (2 if slider._display_step < 0.1 else 1)
        slider._display_var.set(f"{value:.{digits}f}")
        if update:
            self.queue_preview()

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("All files", "*.*")])
        if path:
            self.image_path = path
            self.file_label.configure(text=Path(path).name)
            self.mesh = None
            self.queue_preview()

    def open_svg(self):
        path = filedialog.askopenfilename(filetypes=[("SVG files", "*.svg")])
        if path:
            self.svg_path = path
            self.shape.set("SVG")
            self.queue_preview()

    def shape_changed(self, _=None):
        self.queue_preview()

    def settings(self):
        return MeshSettings(
            width_mm=self.width.get(), base_thickness_mm=self.base.get(),
            design_offset_mm=self.offset.get(), resolution=round(self.resolution.get()),
            relief_mode=self.mode.get(), threshold=self.threshold.get(), response=self.response.get(),
            smoothing=self.smoothing.get(), invert=self.invert.get(), use_baseplate=self.base_on.get(),
            base_shape=self.shape.get(), svg_path=self.svg_path,
            curve_enabled=self.curve_on.get(), curve_radius_mm=self.curve_radius.get(),
            curve_profile=self.curve_profile.get(), curve_axis=self.curve_axis.get(),
            curve_side=self.curve_side.get(), flat_center_mm=self.flat_center.get(),
            side_radius_mm=self.side_radius.get(), side_wrap_degrees=self.side_wrap.get())

    def queue_preview(self):
        self.mesh = None
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(180, self.update_preview)

    def update_preview(self):
        self._preview_job = None
        if not self.image_path:
            return
        try:
            top, mask, _ = prepare_heightmap(self.image_path, self.settings())
            gy, gx = np.gradient(top)
            # Simple directional Lambert-like shading makes depth readable without OpenGL.
            shade = 0.62 + (-gx * 0.8 - gy * 0.55)
            shade = np.clip(shade, 0.18, 1.0)
            shade = (shade * 255).astype("uint8")
            shade[~mask] = 18
            image = Image.fromarray(shade, "L").convert("RGB")
            self.preview_image = image
            self.preview_zoom = 1.0
            self.fit_preview()
            curve_note = " — curve is applied during mesh generation" if self.curve_on.get() else ""
            self.status.configure(text="Preview updated — generate the mesh before export" + curve_note)
        except Exception as exc:
            self.status.configure(text=str(exc))

    def _mouse_zoom(self, event):
        self.zoom_preview(1.15 if event.delta > 0 else 1 / 1.15)

    def zoom_preview(self, factor):
        if self.preview_image is None:
            return
        self.preview_zoom = max(0.05, min(12.0, self.preview_zoom * factor))
        self._draw_preview()

    def fit_preview(self):
        if self.preview_image is None:
            return
        self.preview_canvas.update_idletasks()
        available_w = max(100, self.preview_canvas.winfo_width() - 24)
        available_h = max(100, self.preview_canvas.winfo_height() - 24)
        self.preview_zoom = min(available_w / self.preview_image.width,
                                available_h / self.preview_image.height)
        self._draw_preview(center=True)

    def _draw_preview(self, center=False):
        width = max(1, round(self.preview_image.width * self.preview_zoom))
        height = max(1, round(self.preview_image.height * self.preview_zoom))
        rendered = self.preview_image.resize((width, height), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(rendered)
        canvas_w = max(1, self.preview_canvas.winfo_width())
        canvas_h = max(1, self.preview_canvas.winfo_height())
        area_w, area_h = max(width, canvas_w), max(height, canvas_h)
        origin_x, origin_y = (area_w - width) // 2, (area_h - height) // 2
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(origin_x, origin_y, anchor="nw", image=self.preview_photo)
        self.preview_canvas.configure(scrollregion=(0, 0, area_w, area_h))
        if center:
            self.preview_canvas.xview_moveto(max(0.0, (area_w - canvas_w) / (2 * area_w)))
            self.preview_canvas.yview_moveto(max(0.0, (area_h - canvas_h) / (2 * area_h)))

    def generate_mesh(self, callback=None):
        if not self.image_path:
            messagebox.showinfo("Image required", "Open an image first.")
            return
        self.generate_button.configure(state="disabled")
        self.status.configure(text="Generating watertight mesh…")
        settings = self.settings()
        def work():
            try:
                mesh = build_mesh(self.image_path, settings)
                self.after(0, lambda: self._mesh_done(mesh, callback))
            except Exception as exc:
                self.after(0, lambda e=exc: self._mesh_error(e))
        threading.Thread(target=work, daemon=True).start()

    def _mesh_done(self, mesh, callback):
        self.mesh = mesh
        self.generate_button.configure(state="normal")
        if len(mesh.faces) <= 2_000_000:
            state = "watertight" if mesh.is_watertight else "has open or non-manifold edges"
        else:
            state = "high-density mesh ready"
        self.status.configure(text=f"Mesh ready: {len(mesh.faces):,} triangles, {state}")
        if callback:
            callback()

    def _mesh_error(self, exc):
        self.generate_button.configure(state="normal")
        self.status.configure(text="Mesh generation failed")
        messagebox.showerror("Could not generate mesh", str(exc))

    def show_3d_preview(self):
        if self.mesh is None:
            self.generate_mesh(self._open_3d_viewer)
        else:
            self._open_3d_viewer()

    def _open_3d_viewer(self):
        try:
            MeshViewer(self, self.mesh)
        except Exception as exc:
            messagebox.showerror("3D preview failed", str(exc))

    def export(self, extension):
        def choose_and_write():
            path = filedialog.asksaveasfilename(defaultextension=extension,
                                                filetypes=[(extension.upper()[1:] + " file", "*" + extension)])
            if not path:
                return
            try:
                export_mesh(self.mesh, path)
                self.status.configure(text=f"Exported {Path(path).name}")
            except Exception as exc:
                messagebox.showerror("Export failed", str(exc))
        if self.mesh is None:
            self.generate_mesh(choose_and_write)
        else:
            choose_and_write()


class MeshViewer:
    """Interactive Matplotlib mesh inspector embedded in a CustomTkinter window."""

    MAX_DISPLAY_FACES = 70000

    def __init__(self, parent, mesh):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        from matplotlib.figure import Figure
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        self.mesh = mesh
        self.display_mesh = self._create_display_mesh(mesh)
        self.Poly3DCollection = Poly3DCollection
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Interactive 3D Mesh Preview")
        self.window.geometry("1000x760")
        self.window.minsize(720, 560)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.window)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        count_text = f"Export mesh: {len(mesh.faces):,} triangles"
        if self.display_mesh is not mesh:
            count_text += f" • continuous preview: {len(self.display_mesh.faces):,} triangles"
        ctk.CTkLabel(header, text=count_text).pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Left drag: rotate  •  Middle drag: pan  •  Wheel: zoom").pack(
            side="left", padx=16)
        self.wireframe = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(header, text="Wireframe", variable=self.wireframe,
                        command=self.draw_mesh).pack(side="right", padx=8)
        ctk.CTkButton(header, text="Reset view", width=90, command=self.reset_view).pack(
            side="right", padx=8)

        self.figure = Figure(figsize=(8, 6), dpi=100, facecolor="#17191c")
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.ax.mouse_init(rotate_btn=1, pan_btn=2, zoom_btn=3)
        self.ax.set_facecolor("#17191c")
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.window)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10)
        toolbar_frame = tk.Frame(self.window)
        toolbar_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill="x")
        self.canvas.mpl_connect("scroll_event", self._wheel_zoom)
        self.draw_mesh()
        self.reset_view()
        self.window.after(100, self.window.lift)

    def _create_display_mesh(self, mesh):
        if len(mesh.faces) <= self.MAX_DISPLAY_FACES:
            return mesh
        try:
            # Quadric decimation creates a connected, closed visual approximation.
            # Sampling arbitrary faces would leave gaps and make dense models vanish.
            return mesh.simplify_quadric_decimation(face_count=self.MAX_DISPLAY_FACES)
        except Exception as exc:
            raise RuntimeError(
                "Could not create the optimized viewer mesh. Reinstall the project "
                f"requirements and try again. Details: {exc}"
            ) from exc

    def draw_mesh(self):
        self.ax.clear()
        faces = self.display_mesh.faces
        triangles = self.display_mesh.vertices[faces]
        z_mean = triangles[:, :, 2].mean(axis=1)
        z_range = max(float(np.ptp(z_mean)), 1e-9)
        level = 0.32 + 0.62 * ((z_mean - z_mean.min()) / z_range)
        colors = np.column_stack((level, level, level, np.ones_like(level)))
        edges = "#22272b" if self.wireframe.get() else "none"
        collection = self.Poly3DCollection(triangles, facecolors=colors,
                                           edgecolors=edges,
                                           linewidths=0.18 if self.wireframe.get() else 0)
        self.ax.add_collection3d(collection)
        self._set_equal_limits()
        self._style_axes()
        self.canvas.draw_idle()

    def _set_equal_limits(self):
        bounds = self.mesh.bounds
        center = bounds.mean(axis=0)
        span = max(float(np.max(bounds[1] - bounds[0])), 1.0) * 0.58
        self.base_center = center
        self.base_span = span
        self.ax.set_xlim(center[0] - span, center[0] + span)
        self.ax.set_ylim(center[1] - span, center[1] + span)
        self.ax.set_zlim(center[2] - span, center[2] + span)
        self.ax.set_box_aspect((1, 1, 1))

    def _style_axes(self):
        self.ax.set_xlabel("X (mm)", color="#cccccc")
        self.ax.set_ylabel("Y (mm)", color="#cccccc")
        self.ax.set_zlabel("Z (mm)", color="#cccccc")
        self.ax.tick_params(colors="#aaaaaa")
        for axis in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            axis.pane.set_facecolor((0.10, 0.11, 0.12, 1.0))
            axis.pane.set_edgecolor((0.35, 0.35, 0.35, 1.0))

    def reset_view(self):
        self._set_equal_limits()
        self.ax.view_init(elev=28, azim=-58)
        self.canvas.draw_idle()

    def _wheel_zoom(self, event):
        factor = 0.82 if event.button == "up" else 1.22
        for getter, setter in ((self.ax.get_xlim3d, self.ax.set_xlim3d),
                               (self.ax.get_ylim3d, self.ax.set_ylim3d),
                               (self.ax.get_zlim3d, self.ax.set_zlim3d)):
            low, high = getter()
            middle = (low + high) / 2
            half = (high - low) * factor / 2
            setter(middle - half, middle + half)
        self.canvas.draw_idle()


if __name__ == "__main__":
    ReliefStudio().mainloop()
