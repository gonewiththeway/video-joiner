import subprocess

FFMPEG = "/opt/homebrew/bin/ffmpeg"

def create_ken_burns_smooth(image_path, output_path, duration=10, fps=60, move_pixels=200, zoom_start=1.2, zoom_end=1.3):
    width = 1080
    height = 1920
    total_frames = duration * fps
    zoom_diff = zoom_end - zoom_start

    zoom_expr = f"{zoom_start} + ({zoom_diff}*on/{total_frames})"
    x_expr = f"iw/2 - (iw/{zoom_expr})/2"
    y_expr = f"ih/2 - (ih/{zoom_expr})/2 - {move_pixels}*on/{total_frames}"

    vf = (
        f"zoompan=z='{zoom_expr}':"
        f"x='{x_expr}':"
        f"y='{y_expr}':"
        f"d=1:s={width}x{height},"
        f"fps={fps}"
    )

    cmd = [
        FFMPEG,
        "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        output_path
    ]

    subprocess.run(cmd, check=True)

# Run it
create_ken_burns_smooth(
    "/Users/atulpurohit/workspace/personal/video/output/9/1.png",
    "/Users/atulpurohit/workspace/personal/video/output/9/output.mp4"
)
