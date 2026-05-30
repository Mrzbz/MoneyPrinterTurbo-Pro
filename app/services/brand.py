"""
Brand Customization Service for MoneyPrinterTurbo Pro.

Provides logo watermark placement, intro/outro video generation,
color scheme management, font settings, and social media handles overlay.
"""

import os
import json
import subprocess
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WatermarkPosition(Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"


class IntroStyle(Enum):
    FADE_IN = "fade_in"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_IN = "zoom_in"
    TYPEWRITER = "typewriter"
    GLITCH = "glitch"


class OutroStyle(Enum):
    FADE_OUT = "fade_out"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_OUT = "zoom_out"
    BLUR = "blur"


@dataclass
class ColorScheme:
    """Represents a brand color scheme."""
    primary: str = "#FFFFFF"
    secondary: str = "#000000"
    accent: str = "#007BFF"
    background: str = "#1A1A2E"
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#CCCCCC"
    gradient_start: str = "#667eea"
    gradient_end: str = "#764ba2"

    def to_ffmpeg_color(self, hex_color: str) -> str:
        """Convert hex color to ffmpeg-compatible format."""
        return hex_color.replace("#", "0x")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FontSettings:
    """Font configuration for brand elements."""
    primary_font: str = "Arial"
    secondary_font: str = "Helvetica"
    title_size: int = 48
    subtitle_size: int = 32
    body_size: int = 24
    watermark_size: int = 16
    social_handle_size: int = 20
    font_weight: str = "bold"
    font_file: Optional[str] = None

    def get_ffmpeg_font_filter(self, text: str, size: Optional[int] = None,
                                color: str = "#FFFFFF") -> str:
        """Build an ffmpeg drawtext filter string for the given parameters."""
        sz = size or self.body_size
        font_name = self.primary_font
        font_part = f"fontfile='{self.font_file}'" if self.font_file else f"font='{font_name}'"
        return f"drawtext={font_part}:fontsize={sz}:fontcolor={color}:text='{text}'"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SocialHandle:
    """A single social media handle entry."""
    platform: str
    handle: str
    icon_path: Optional[str] = None


@dataclass
class BrandProfile:
    """Full brand profile configuration."""
    name: str = "Default Brand"
    logo_path: Optional[str] = None
    watermark_path: Optional[str] = None
    watermark_position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    watermark_opacity: float = 0.7
    watermark_size_percent: int = 10
    color_scheme: ColorScheme = field(default_factory=ColorScheme)
    font_settings: FontSettings = field(default_factory=FontSettings)
    social_handles: list = field(default_factory=list)
    intro_duration: float = 3.0
    intro_style: IntroStyle = IntroStyle.FADE_IN
    outro_duration: float = 3.0
    outro_style: OutroStyle = OutroStyle.FADE_OUT
    intro_text: str = ""
    outro_text: str = ""
    intro_audio: Optional[str] = None
    outro_audio: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["watermark_position"] = self.watermark_position.value
        d["intro_style"] = self.intro_style.value
        d["outro_style"] = self.outro_style.value
        return d


def _pos_to_xy(position: WatermarkPosition, vw: int = 1920, vh: int = 1080,
               pad: int = 20, logo_w: int = 0, logo_h: int = 0) -> tuple:
    """Map a WatermarkPosition enum to pixel (x, y) coordinates."""
    cx = (vw - logo_w) // 2
    cy = (vh - logo_h) // 2
    mapping = {
        WatermarkPosition.TOP_LEFT: (pad, pad),
        WatermarkPosition.TOP_RIGHT: (vw - logo_w - pad, pad),
        WatermarkPosition.BOTTOM_LEFT: (pad, vh - logo_h - pad),
        WatermarkPosition.BOTTOM_RIGHT: (vw - logo_w - pad, vh - logo_h - pad),
        WatermarkPosition.CENTER: (cx, cy),
        WatermarkPosition.TOP_CENTER: (cx, pad),
        WatermarkPosition.BOTTOM_CENTER: (cx, vh - logo_h - pad),
    }
    return mapping.get(position, (vw - logo_w - pad, vh - logo_h - pad))


class BrandManager:
    """
    Central manager for all brand-related operations.

    Supports loading/saving brand profiles, generating watermark overlays,
    creating intro/outro videos via ffmpeg, managing color schemes, and
    overlaying social media handles.
    """

    DEFAULT_PROFILES_DIR = "brand_profiles"

    def __init__(self, profiles_dir: Optional[str] = None):
        self.profiles_dir = profiles_dir or self.DEFAULT_PROFILES_DIR
        self.profiles: dict[str, BrandProfile] = {}
        self.active_profile: Optional[BrandProfile] = None
        self._ensure_profiles_dir()

    def _ensure_profiles_dir(self) -> None:
        os.makedirs(self.profiles_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------
    def create_profile(self, name: str, **kwargs) -> BrandProfile:
        """Create a new brand profile and persist it."""
        profile = BrandProfile(name=name, **kwargs)
        self.profiles[name] = profile
        self.save_profile(profile)
        logger.info("Created brand profile '%s'", name)
        return profile

    def save_profile(self, profile: BrandProfile) -> str:
        """Serialize a profile to JSON on disk."""
        path = os.path.join(self.profiles_dir, f"{profile.name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(profile.to_dict(), fh, indent=2)
        return path

    def load_profile(self, name: str) -> BrandProfile:
        """Load a brand profile from disk by name."""
        path = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Brand profile not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        data["watermark_position"] = WatermarkPosition(data.get("watermark_position", "bottom_right"))
        data["intro_style"] = IntroStyle(data.get("intro_style", "fade_in"))
        data["outro_style"] = OutroStyle(data.get("outro_style", "fade_out"))
        data["color_scheme"] = ColorScheme(**data.get("color_scheme", {}))
        data["font_settings"] = FontSettings(**data.get("font_settings", {}))
        handles = [SocialHandle(**h) for h in data.get("social_handles", [])]
        data["social_handles"] = handles
        profile = BrandProfile(**data)
        self.profiles[name] = profile
        return profile

    def list_profiles(self) -> list[str]:
        """Return a list of saved profile names."""
        return [
            f.stem for f in Path(self.profiles_dir).glob("*.json")
        ]

    def set_active(self, name: str) -> BrandProfile:
        """Load and activate a brand profile."""
        if name not in self.profiles:
            self.load_profile(name)
        self.active_profile = self.profiles[name]
        logger.info("Active brand profile set to '%s'", name)
        return self.active_profile

    def get_active(self) -> BrandProfile:
        if self.active_profile is None:
            raise RuntimeError("No active brand profile. Call set_active() first.")
        return self.active_profile

    # ------------------------------------------------------------------
    # Watermark / Logo Overlay
    # ------------------------------------------------------------------
    def build_watermark_filter(
        self,
        logo_path: Optional[str] = None,
        position: Optional[WatermarkPosition] = None,
        opacity: Optional[float] = None,
        size_percent: Optional[int] = None,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> str:
        """
        Build an ffmpeg filter-graph string that overlays a logo watermark.

        Returns a filter string like:
            [1:v]format=rgba,colorchannelmixer=aa=0.7[wm];[0:v][wm]overlay=...
        """
        profile = self.get_active()
        logo = logo_path or profile.watermark_path or profile.logo_path
        if not logo:
            raise ValueError("No logo/watermark path provided and none configured in profile.")

        pos = position or profile.watermark_position
        alpha = opacity if opacity is not None else profile.watermark_opacity
        pct = size_percent if size_percent is not None else profile.watermark_size_percent

        # Scale the logo to the desired percentage of the video height
        scaled_h = int(video_height * pct / 100)
        x, y = _pos_to_xy(pos, vw=video_width, vh=video_height, logo_h=scaled_h)

        # Build the filter chain
        filters = (
            f"[1:v]scale=-1:{scaled_h},format=rgba,"
            f"colorchannelmixer=aa={alpha}[wm];"
            f"[0:v][wm]overlay={x}:{y}:eof_action=pass"
        )
        return filters

    def apply_watermark(self, input_video: str, output_video: str,
                        logo_path: Optional[str] = None,
                        position: Optional[WatermarkPosition] = None,
                        opacity: Optional[float] = None,
                        size_percent: Optional[int] = None) -> str:
        """
        Apply a logo watermark to a video file using ffmpeg.

        Returns the path to the output video.
        """
        profile = self.get_active()
        logo = logo_path or profile.watermark_path or profile.logo_path
        if not logo or not os.path.isfile(logo):
            raise FileNotFoundError(f"Logo file not found: {logo}")

        wm_filter = self.build_watermark_filter(
            logo_path=logo, position=position,
            opacity=opacity, size_percent=size_percent,
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-i", logo,
            "-filter_complex", wm_filter,
            "-map", "0:a?",
            "-c:a", "copy",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            output_video,
        ]
        logger.info("Applying watermark: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return output_video

    # ------------------------------------------------------------------
    # Intro Video Generation
    # ------------------------------------------------------------------
    def generate_intro(self, output_path: str, duration: Optional[float] = None,
                       style: Optional[IntroStyle] = None,
                       text: Optional[str] = None, width: int = 1920,
                       height: int = 1080) -> str:
        """Generate an intro video clip using ffmpeg."""
        profile = self.get_active()
        dur = duration or profile.intro_duration
        stl = style or profile.intro_style
        txt = text or profile.intro_text or profile.name
        colors = profile.color_scheme
        fonts = profile.font_settings

        bg_color = colors.to_ffmpeg_color(colors.background)
        text_color = colors.to_ffmpeg_color(colors.text_primary)
        accent_color = colors.to_ffmpeg_color(colors.accent)

        # Base: solid color background
        base_filter = f"color=c=0x{bg_color.replace('0x','')}:s={width}x{height}:d={dur}:r=30"

        # Build style-specific animation filters
        drawtext_common = (
            f"fontsize={fonts.title_size}:fontcolor={text_color}:"
            f"x=(w-text_w)/2:y=(h-text_h)/2"
        )
        if fonts.font_file:
            drawtext_common = f"fontfile='{fonts.font_file}':{drawtext_common}"
        else:
            drawtext_common = f"font='{fonts.primary_font}':{drawtext_common}"

        if stl == IntroStyle.FADE_IN:
            fade_filter = f"drawtext={drawtext_common}:text='{txt}':alpha='if(lt(t,1),t,1)'"
        elif stl == IntroStyle.SLIDE_LEFT:
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"x='if(lt(t,1),w-w*t,(w-text_w)/2)'"
            )
        elif stl == IntroStyle.SLIDE_RIGHT:
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"x='if(lt(t,1),-text_w+text_w*w/w*t+w*t,(w-text_w)/2)'"
            )
        elif stl == IntroStyle.ZOOM_IN:
            zoom_size = int(fonts.title_size * 1.5)
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"fontsize='if(lt(t,1),{fonts.title_size}+{zoom_size}*t,{zoom_size*2})'"
            )
        elif stl == IntroStyle.TYPEWRITER:
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"enable='gte(t,0.5)'"
            )
        elif stl == IntroStyle.GLITCH:
            fade_filter = f"drawtext={drawtext_common}:text='{txt}'"
        else:
            fade_filter = f"drawtext={drawtext_common}:text='{txt}'"

        # Add optional accent bar / gradient overlay
        full_filter = f"{base_filter},{fade_filter}"

        # Add logo overlay if available
        inputs = ["-f", "lavfi", "-i", full_filter]
        logo_path = profile.logo_path
        if logo_path and os.path.isfile(logo_path):
            inputs.extend(["-i", logo_path])
            logo_size = int(height * 0.15)
            x, y = _pos_to_xy(WatermarkPosition.TOP_CENTER, vw=width, vh=height,
                               logo_h=logo_size)
            wm_part = (
                f"[1:v]scale=-1:{logo_size},format=rgba,"
                f"colorchannelmixer=aa=0.9[logo];"
                f"[0:v][logo]overlay={x}:{y}[out]"
            )
            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", wm_part,
                "-map", "[out]",
                "-t", str(dur),
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                output_path,
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-t", str(dur),
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                output_path,
            ]

        logger.info("Generating intro: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Mix intro audio if configured
        if profile.intro_audio and os.path.isfile(profile.intro_audio):
            self._mix_audio(output_path, profile.intro_audio, output_path)

        return output_path

    # ------------------------------------------------------------------
    # Outro Video Generation
    # ------------------------------------------------------------------
    def generate_outro(self, output_path: str, duration: Optional[float] = None,
                       style: Optional[OutroStyle] = None,
                       text: Optional[str] = None, width: int = 1920,
                       height: int = 1080) -> str:
        """Generate an outro video clip using ffmpeg."""
        profile = self.get_active()
        dur = duration or profile.outro_duration
        stl = style or profile.outro_style
        txt = text or profile.outro_text or "Thanks for watching"
        colors = profile.color_scheme
        fonts = profile.font_settings

        bg_color = colors.to_ffmpeg_color(colors.background)
        text_color = colors.to_ffmpeg_color(colors.text_primary)

        base_filter = f"color=c=0x{bg_color.replace('0x','')}:s={width}x{height}:d={dur}:r=30"

        drawtext_common = (
            f"fontsize={fonts.title_size}:fontcolor={text_color}:"
            f"x=(w-text_w)/2:y=(h-text_h)/2"
        )
        if fonts.font_file:
            drawtext_common = f"fontfile='{fonts.font_file}':{drawtext_common}"
        else:
            drawtext_common = f"font='{fonts.primary_font}':{drawtext_common}"

        if stl == OutroStyle.FADE_OUT:
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"alpha='if(lt(t,{dur-1}),1,1-(t-{dur-1}))'"
            )
        elif stl == OutroStyle.SLIDE_LEFT:
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"x='if(gt(t,{dur-1}),(w-text_w)/2-(w)*(t-{dur-1}),(w-text_w)/2)'"
            )
        elif stl == OutroStyle.SLIDE_RIGHT:
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"x='if(gt(t,{dur-1}),(w-text_w)/2+(w)*(t-{dur-1}),(w-text_w)/2)'"
            )
        elif stl == OutroStyle.ZOOM_OUT:
            fade_filter = (
                f"drawtext={drawtext_common}:text='{txt}':"
                f"fontsize='if(gt(t,{dur-1}),{fonts.title_size}*(1-(t-{dur-1})),{fonts.title_size})'"
            )
        elif stl == OutroStyle.BLUR:
            fade_filter = f"drawtext={drawtext_common}:text='{txt}'"
        else:
            fade_filter = f"drawtext={drawtext_common}:text='{txt}'"

        full_filter = f"{base_filter},{fade_filter}"

        # Add social handles overlay
        social_filter = self._build_social_overlay_filter(width, height, fonts, colors)
        if social_filter:
            full_filter += f",{social_filter}"

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", full_filter,
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            output_path,
        ]
        logger.info("Generating outro: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        if profile.outro_audio and os.path.isfile(profile.outro_audio):
            self._mix_audio(output_path, profile.outro_audio, output_path)

        return output_path

    # ------------------------------------------------------------------
    # Social Media Handles Overlay
    # ------------------------------------------------------------------
    def _build_social_overlay_filter(self, width: int, height: int,
                                      fonts: Optional[FontSettings] = None,
                                      colors: Optional[ColorScheme] = None) -> str:
        """Build a comma-separated chain of drawtext filters for social handles."""
        profile = self.get_active()
        if not profile.social_handles:
            return ""

        fonts = fonts or profile.font_settings
        colors = colors or profile.color_scheme
        text_color = colors.to_ffmpeg_color(colors.text_secondary)
        sz = fonts.social_handle_size

        parts = []
        y_offset = height - 60
        for i, handle in enumerate(profile.social_handles):
            label = f"@{handle.handle}" if not handle.handle.startswith("@") else handle.handle
            platform_label = f"{handle.platform}: {label}"
            # Stagger handles horizontally
            x_pos = 40 + i * 250
            font_part = f"fontfile='{fonts.font_file}'" if fonts.font_file else f"font='{fonts.primary_font}'"
            part = (
                f"drawtext={font_part}:fontsize={sz}:"
                f"fontcolor={text_color}:"
                f"x={x_pos}:y={y_offset}:"
                f"text='{platform_label}'"
            )
            parts.append(part)

        return ",".join(parts)

    def add_social_handle(self, platform: str, handle: str,
                          icon_path: Optional[str] = None) -> None:
        """Add a social media handle to the active profile."""
        profile = self.get_active()
        profile.social_handles.append(
            SocialHandle(platform=platform, handle=handle, icon_path=icon_path)
        )
        self.save_profile(profile)
        logger.info("Added social handle %s:%s to profile '%s'",
                     platform, handle, profile.name)

    def remove_social_handle(self, platform: str) -> None:
        """Remove a social handle by platform name from the active profile."""
        profile = self.get_active()
        profile.social_handles = [
            h for h in profile.social_handles if h.platform != platform
        ]
        self.save_profile(profile)

    # ------------------------------------------------------------------
    # Color Scheme Management
    # ------------------------------------------------------------------
    def update_color_scheme(self, **kwargs) -> ColorScheme:
        """Update one or more color values on the active profile."""
        profile = self.get_active()
        scheme = profile.color_scheme
        for key, value in kwargs.items():
            if hasattr(scheme, key):
                setattr(scheme, key, value)
            else:
                logger.warning("Unknown color key '%s', skipping", key)
        self.save_profile(profile)
        return scheme

    def get_color_scheme(self) -> ColorScheme:
        """Return the current active color scheme."""
        return self.get_active().color_scheme

    def apply_color_preset(self, preset_name: str) -> ColorScheme:
        """Apply a built-in color preset."""
        presets = {
            "dark": ColorScheme(
                primary="#FFFFFF", secondary="#AAAAAA", accent="#007BFF",
                background="#1A1A2E", text_primary="#FFFFFF", text_secondary="#CCCCCC",
                gradient_start="#667eea", gradient_end="#764ba2",
            ),
            "light": ColorScheme(
                primary="#000000", secondary="#555555", accent="#0056b3",
                background="#F5F5F5", text_primary="#000000", text_secondary="#333333",
                gradient_start="#ffecd2", gradient_end="#fcb69f",
            ),
            "neon": ColorScheme(
                primary="#00FF88", secondary="#FF00FF", accent="#FFFF00",
                background="#0D0D0D", text_primary="#00FF88", text_secondary="#AAAAAA",
                gradient_start="#f7971e", gradient_end="#ffd200",
            ),
            "corporate": ColorScheme(
                primary="#1E3A5F", secondary="#4A6FA5", accent="#E8A838",
                background="#FFFFFF", text_primary="#1E3A5F", text_secondary="#666666",
                gradient_start="#2c3e50", gradient_end="#3498db",
            ),
            "minimal": ColorScheme(
                primary="#333333", secondary="#999999", accent="#FF4444",
                background="#FAFAFA", text_primary="#333333", text_secondary="#888888",
                gradient_start="#232526", gradient_end="#414345",
            ),
        }
        if preset_name not in presets:
            raise ValueError(f"Unknown preset '{preset_name}'. Available: {list(presets.keys())}")
        profile = self.get_active()
        profile.color_scheme = presets[preset_name]
        self.save_profile(profile)
        return presets[preset_name]

    # ------------------------------------------------------------------
    # Font Settings Management
    # ------------------------------------------------------------------
    def update_font_settings(self, **kwargs) -> FontSettings:
        """Update font settings on the active profile."""
        profile = self.get_active()
        settings = profile.font_settings
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
            else:
                logger.warning("Unknown font setting '%s', skipping", key)
        self.save_profile(profile)
        return settings

    def get_font_settings(self) -> FontSettings:
        return self.get_active().font_settings

    # ------------------------------------------------------------------
    # Concatenation Helpers
    # ------------------------------------------------------------------
    def concat_intro_main_outro(self, intro_path: str, main_video: str,
                                 outro_path: str, output_path: str) -> str:
        """Concatenate intro + main video + outro into a single file."""
        concat_file = os.path.join(os.path.dirname(output_path), "_concat_list.txt")
        lines = [
            f"file '{os.path.abspath(intro_path)}'",
            f"file '{os.path.abspath(main_video)}'",
            f"file '{os.path.abspath(outro_path)}'",
        ]
        with open(concat_file, "w") as fh:
            fh.write("\n".join(lines))

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            output_path,
        ]
        logger.info("Concatenating intro+main+outro: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Clean up temp file
        if os.path.exists(concat_file):
            os.remove(concat_file)

        return output_path

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _mix_audio(video_path: str, audio_path: str, output_path: str) -> None:
        """Mix an audio track into a video (replacing existing audio)."""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    @staticmethod
    def get_video_dimensions(video_path: str) -> tuple[int, int]:
        """Probe video dimensions using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.strip().split("x")
        return int(parts[0]), int(parts[1])

    # ------------------------------------------------------------------
    # Full Brand Application Pipeline
    # ------------------------------------------------------------------
    def apply_full_branding(
        self,
        main_video: str,
        output_path: str,
        include_intro: bool = True,
        include_outro: bool = True,
        include_watermark: bool = True,
    ) -> str:
        """
        End-to-end pipeline: optionally generate intro/outro, apply watermark,
        concatenate everything, and produce the final branded video.
        """
        profile = self.get_active()
        work_dir = os.path.dirname(output_path) or "."
        w, h = self.get_video_dimensions(main_video)

        parts_to_concat = []
        temp_files = []

        # Intro
        if include_intro:
            intro_out = os.path.join(work_dir, "_brand_intro.mp4")
            self.generate_intro(intro_out, width=w, height=h)
            parts_to_concat.append(intro_out)
            temp_files.append(intro_out)

        # Watermarked main
        if include_watermark:
            watermarked = os.path.join(work_dir, "_brand_watermarked.mp4")
            self.apply_watermark(main_video, watermarked)
            parts_to_concat.append(watermarked)
            temp_files.append(watermarked)
        else:
            parts_to_concat.append(main_video)

        # Outro
        if include_outro:
            outro_out = os.path.join(work_dir, "_brand_outro.mp4")
            self.generate_outro(outro_out, width=w, height=h)
            parts_to_concat.append(outro_out)
            temp_files.append(outro_out)

        # Concatenate if multiple parts
        if len(parts_to_concat) == 1:
            # Just rename/copy the single part
            os.rename(parts_to_concat[0], output_path)
        else:
            self.concat_intro_main_outro(
                parts_to_concat[0], parts_to_concat[1],
                parts_to_concat[2] if len(parts_to_concat) > 2 else parts_to_concat[1],
                output_path,
            )

        # Clean up temporary files
        for tf in temp_files:
            if os.path.exists(tf) and tf != output_path:
                os.remove(tf)

        logger.info("Full branding complete: %s", output_path)
        return output_path
