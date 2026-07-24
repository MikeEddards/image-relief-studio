# Image Generation Guide for Image Relief Studio

## Purpose

Use this document when generating source artwork for **Image Relief Studio**, which
converts a 2D image into a printable STL or 3MF relief model.

The source image is not treated like a normal photograph. Its brightness is used as
height information:

- **Black = lowest surface / no added relief**
- **Dark gray = shallow relief**
- **Medium gray = medium relief**
- **Light gray = high relief**
- **White = maximum relief**

When the software's **Invert image** option is enabled, this relationship is reversed.
Unless explicitly requested otherwise, generate images using the normal relationship:
black is low and white is high.

## Primary Goal

Create a clean, detailed, two-tone grayscale relief map rather than a realistic color
illustration. The final image should look like a professionally sculpted bas-relief
rendered with controlled grayscale height transitions.

The artwork should contain:

1. A uniform black or very dark background.
2. A clearly separated light-gray or white subject.
3. Smooth internal gradients that describe the subject's height and curvature.
4. Sharp, readable silhouettes without glow, cast shadows, or background texture.

## Required Image Characteristics

### Color and Tonal Range

- Generate in grayscale only.
- Use neutral grays with equal red, green, and blue values.
- Do not introduce colored pixels, sepia tones, blue highlights, or warm lighting.
- Use a pure or nearly pure black background: RGB `0, 0, 0` is preferred.
- Use light gray through white for the raised design.
- Reserve pure white for the highest points of the design.
- Keep important intermediate heights visibly separated.
- Avoid crushed whites where large areas become completely white and lose detail.
- Avoid muddy, low-contrast gray-on-gray artwork.

Although the requested visual style is “two tone,” the subject should contain smooth
grayscale transitions between its dark and light endpoints. The two dominant regions
are the dark background and light design; the internal gradient communicates depth.

### Background

- The background must be perfectly flat and uniform.
- Do not add paper grain, noise, stars, dust, fog, vignettes, gradients, or texture to
  the background unless those elements are intentionally part of the printable design.
- Do not add cast shadows behind the subject. A cast shadow becomes unintended raised
  geometry.
- For use with a baseplate, an opaque black background is ideal.
- For a design-only model without a baseplate, a transparent background is preferred.
  If transparency is unavailable, use pure black with a clean boundary.

### Subject Silhouette

- Give every printable element a clean, closed, unambiguous silhouette.
- Keep the outer boundary crisp and high contrast against the background.
- Avoid fuzzy edges, bloom, halos, motion blur, depth-of-field blur, and antialiased
  glow extending into the background.
- Normal one- or two-pixel edge antialiasing is acceptable.
- Do not allow separate parts to touch accidentally.
- Connect elements that must print as one design, or leave deliberate spacing between
  independent elements.
- Avoid extremely thin lines and tiny isolated dots unless the target print size can
  support them.

As a general rule, important lines should be at least **1 mm wide in the final model**.
For an 80 mm-wide model generated from a 1024-pixel image, 1 mm is approximately 13
pixels. Finer details may disappear due to printer resolution, mesh resolution, or
image smoothing.

### Height and Gradient Construction

Treat brightness as physical height, not as simulated illumination.

- Gradients should follow the shape's intended surface curvature.
- Use darker gray where a feature meets the base.
- Transition smoothly toward lighter values at raised ridges, centers, or peaks.
- Keep equal-height areas at equal brightness.
- Use symmetrical gradients for symmetrical features.
- Use broad gradients for smooth domes and narrow gradients for sharp ridges.
- Separate overlapping forms with a clear tonal step when they need different heights.
- Avoid gradients caused only by imaginary directional lighting.
- Do not add specular reflections, metallic reflections, environmental reflections, or
  glossy highlights. These create false bumps in the exported model.
- Do not add ambient-occlusion shadows unless a darker recessed region is genuinely
  intended there.

The image should still make structural sense if interpreted purely as a topographic
map: every brighter area will physically rise above every darker neighboring area.

## Two Supported Artwork Styles

### Style A: Smooth Brightness Relief

Use this for rounded, carved, embossed, sculpted, or dimensional designs.

- Create continuous grayscale gradients inside the subject.
- Use several distinct height bands connected by smooth transitions.
- Make broad surfaces smooth and free from noise.
- Use white sparingly for the highest ridges and peaks.
- Make recesses dark gray or black depending on how deep they should be.
- Ensure decorative detail is represented by deliberate brightness changes.

Recommended software settings:

- Relief mode: **Brightness**
- Brightness response: start at `1.0`
- Smoothing: start between `0.5` and `1.5`
- Design offset: positive for embossing, negative for engraving

### Style B: Flat Two-Level Relief

Use this for logos, silhouettes, line art, stamps, signs, and designs where all artwork
should have the same height.

- Use pure black for the background.
- Use white or very light gray for all printable design areas.
- Avoid internal shading and gradients.
- Make boundaries crisp and closed.
- Remove shadows, bevels, reflections, highlights, and texture.
- Ensure small features are thick enough to print.

Recommended software settings:

- Relief mode: **Flat**
- Flat-mode threshold: start at `0.5`
- Smoothing: `0` to `0.5`
- Design offset: positive for raised artwork, negative for recessed artwork

## Composition Rules

- Center the design unless an alternate placement is explicitly requested.
- Leave a safe margin around the artwork. A margin of 5–10% of the image width is a
  good default.
- Do not crop important shapes at the image boundary.
- Use a straight-on orthographic view.
- Do not use perspective, a tilted camera, isometric projection, or foreshortening.
- Do not depict the design already mounted on a physical object unless that entire
  object is supposed to become geometry.
- Do not generate a photographed coin, plaque, carving, pendant, or sculpture. Generate
  the height-map artwork that would be placed on such an object.
- Avoid text unless spelling, font style, and orientation have been explicitly given.
- If text is included, render it cleanly, horizontally, and at a printable thickness.

## Resolution and File Format

- Preferred working resolution: **1024 × 1024 pixels or larger**.
- For tall or wide artwork, preserve the requested aspect ratio rather than forcing a
  square canvas.
- Preferred format: **PNG**.
- Use 8-bit grayscale or 8-bit RGB/RGBA PNG.
- Use transparency only for design-only artwork; otherwise use an opaque black
  background.
- Do not save as a heavily compressed JPEG.
- Do not upscale a small, blurry source image merely to meet the pixel dimensions.

## Features to Avoid

Never add any of the following unless specifically requested as printable geometry:

- Drop shadows or cast shadows
- Glow, bloom, halos, or luminous haze
- Film grain, paper grain, scratches, or random noise
- Photographic lighting
- Metallic or glass reflections
- Colored lighting or colored backgrounds
- Background scenery
- Depth-of-field blur
- Perspective distortion
- Floating dust or particles
- Watermarks, signatures, borders, labels, or mockup elements
- Fake 3D plate edges around the image
- Uncontrolled tiny dots or disconnected fragments

## Standard Generation Prompt

Use this template for smooth relief artwork:

> Create a clean grayscale height map for 3D bas-relief conversion. Depict [SUBJECT]
> in a straight-on orthographic view, centered with a 7% safe margin. Use a perfectly
> uniform pure-black background representing the lowest height. Render the subject in
> neutral gray through white, where brighter values represent physically higher
> surfaces and darker values represent lower surfaces. Build the form with smooth,
> deliberate grayscale gradients that describe actual surface height, not directional
> lighting. Use crisp closed silhouettes and printable feature thicknesses. Reserve
> pure white for the highest ridges and peaks. No color, cast shadows, drop shadows,
> glow, reflections, metallic shine, texture, noise, perspective, scenery, border,
> text, or watermark. Output a high-resolution PNG-style image suitable as a height
> map for 3D printing.

Replace `[SUBJECT]` with a precise description of the desired design.

## Flat-Relief Generation Prompt

Use this template for a two-level design:

> Create a strict two-level black-and-white relief mask of [SUBJECT]. Use a perfectly
> uniform pure-black background and solid white printable design shapes. Use a
> straight-on orthographic view, centered with a 7% safe margin. All white areas must
> represent one equal raised height. Use crisp, closed boundaries and sufficiently
> thick printable lines. No grayscale shading, bevels, cast shadows, glow, blur,
> reflections, texture, noise, perspective, scenery, border, watermark, or unintended
> isolated fragments. Output a high-resolution PNG-style image.

## Negative Prompt

When the image generator supports a separate negative prompt, use:

> color, colored lighting, photograph, realistic lighting, directional shadow, cast
> shadow, drop shadow, ambient shadow, glow, bloom, halo, metallic reflection, glossy
> reflection, glass, sparkle glare, background texture, grain, noise, scratches, fog,
> scenery, perspective, tilted view, isometric view, depth of field, blur, mockup,
> physical plaque, frame, border, watermark, signature, caption, accidental text,
> cropped subject, fuzzy silhouette, tiny disconnected debris

## Example: Moon and Stars

> Create a clean grayscale height map for 3D bas-relief conversion featuring a large
> crescent moon, several four-point stars, small round stars, and three simple
> constellations. Use a straight-on orthographic composition on a perfectly uniform
> pure-black background. Arrange the elements clearly with deliberate spacing and a
> 7% safe margin. The crescent should rise smoothly from dark gray along its boundary
> to light gray and white along its central ridge. Each four-point star should have a
> smooth symmetrical gradient rising to a white center ridge. Constellation lines must
> be thick, connected, and light gray, with round nodes rising slightly higher in near
> white. Brightness must represent physical height rather than illumination. Use crisp
> closed silhouettes. No cast shadows, glow, metallic reflections, photographic
> lighting, texture, noise, color, perspective, border, text, or watermark.

## Pre-Delivery Validation Checklist

Before delivering an image, verify all of the following:

- [ ] The image is grayscale with no color tint.
- [ ] The background is uniformly black or transparent as requested.
- [ ] Black represents the lowest surface and white represents the highest surface.
- [ ] Gradients describe physical height rather than lighting or reflection.
- [ ] The subject has a clean, crisp silhouette.
- [ ] There are no cast shadows, glows, halos, reflections, or background textures.
- [ ] Important lines and isolated features are thick enough to print.
- [ ] Equal-height features use consistent brightness.
- [ ] The artwork is straight-on with no perspective distortion.
- [ ] Important content has not been cropped.
- [ ] A safe margin remains around the subject.
- [ ] The resolution is at least 1024 pixels on the longest side.
- [ ] The final file is preferably PNG.
- [ ] The output contains only intended printable geometry.

## Final Instruction to the Image-Generation Agent

When visual attractiveness conflicts with clean height information, prioritize the
height information. The image will be interpreted numerically and converted into a
physical mesh. Decorative lighting effects that look appealing in a normal image often
become unwanted bumps, trenches, ridges, and fragments in the printed model.
