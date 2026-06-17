"""
creative.py
===========
Ad-copy and creative-brief generation.

Offline default: a deterministic, template-driven generator that produces
platform-shaped copy with the *named fields each platform actually uses*:

  google   — RSA: multiple headlines + multiple descriptions
  meta     — primary text, single headline, call-to-action
  linkedin — intro text, single headline, description

plus an image prompt you can hand to one of the creative models listed in the
awesome list (Imagen 4, Flux, Veo, Runway). This stays a *supporting* feature —
no API calls, no real image/video generation.

Going live: swap `generate_copy` to call an LLM and feed `image_prompt` to a
text-to-image MCP tool. The `CreativeSet` shape stays the same.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Per-platform creative character limits — enforced so generated copy is
# actually uploadable. (Approximate, sufficient for an offline demo.)
LIMITS = {
    "google":   dict(headline=30, description=90, n_headlines=5, n_descriptions=3),
    "meta":     dict(headline=40, primary_text=125, n_headlines=1),
    "linkedin": dict(headline=70, intro_text=150, description=100),
}


@dataclass
class CreativeSet:
    platform: str
    # Google RSA (lists). Single-headline platforms use headlines[0].
    headlines: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    # Meta named fields.
    primary_text: str = ""
    # LinkedIn named fields.
    intro_text: str = ""
    description: str = ""
    call_to_action: str = "Learn more"
    image_prompt: str = ""

    def validate(self) -> list[str]:
        lim = LIMITS[self.platform]
        problems: list[str] = []
        for h in self.headlines:
            if len(h) > lim.get("headline", 9999):
                problems.append(f"headline too long ({len(h)}>{lim['headline']}): {h!r}")
        for d in self.descriptions:
            if len(d) > lim.get("description", 9999):
                problems.append(f"description too long ({len(d)}>{lim['description']}): {d!r}")
        if self.primary_text and len(self.primary_text) > lim.get("primary_text", 9999):
            problems.append(f"primary text too long ({len(self.primary_text)})")
        if self.intro_text and len(self.intro_text) > lim.get("intro_text", 9999):
            problems.append(f"intro text too long ({len(self.intro_text)})")
        if self.description and len(self.description) > lim.get("description", 9999):
            problems.append(f"description too long ({len(self.description)})")
        return problems

    def named_fields(self) -> list[tuple[str, str]]:
        """(label, value) pairs for display, in platform-appropriate order."""
        if self.platform == "google":
            out = [(f"Headline {i+1}", h) for i, h in enumerate(self.headlines)]
            out += [(f"Description {i+1}", d) for i, d in enumerate(self.descriptions)]
            return out
        if self.platform == "meta":
            return [("Primary text", self.primary_text),
                    ("Headline", self.headlines[0] if self.headlines else ""),
                    ("Call to action", self.call_to_action)]
        if self.platform == "linkedin":
            return [("Intro text", self.intro_text),
                    ("Headline", self.headlines[0] if self.headlines else ""),
                    ("Description", self.description)]
        return []


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def generate_copy(*, product: str, audience: str, value_props: list[str],
                  platform: str, cta: str = "Shop now") -> CreativeSet:
    """Template-based copy generator. Deterministic and offline."""
    lim = LIMITS[platform]
    vp = value_props + ["Trusted by thousands", "Fast, free shipping", "30-day guarantee"]

    image_prompt = (
        f"High-quality advertising photograph of {product}, appealing to {audience}, "
        f"emphasising '{vp[0].lower()}'. Clean studio lighting, lifestyle context, "
        f"space for text overlay, brand-neutral, 4:5 aspect ratio. "
        f"[Send to Imagen 4 / Flux / Runway]"
    )

    if platform == "google":
        headlines = [
            f"{product} for {audience}", vp[0], f"Meet {product}",
            f"{vp[1]} on {product}", f"Why {audience} choose {product}",
        ]
        descriptions = [
            f"{product} built for {audience}. {vp[0]}. {cta}.",
            f"{vp[1]} and {vp[2].lower()}. Discover {product} today.",
            f"Join {audience} who switched to {product}. {cta}.",
        ]
        cs = CreativeSet(
            platform=platform,
            headlines=[_truncate(h, lim["headline"]) for h in headlines][: lim["n_headlines"]],
            descriptions=[_truncate(d, lim["description"]) for d in descriptions][: lim["n_descriptions"]],
            call_to_action=cta, image_prompt=image_prompt)

    elif platform == "meta":
        cs = CreativeSet(
            platform=platform,
            headlines=[_truncate(f"{vp[0]} — {product}", lim["headline"])],
            primary_text=_truncate(
                f"{product} built for {audience}. {vp[0]} and {vp[1].lower()}. "
                f"Join thousands who made the switch.", lim["primary_text"]),
            call_to_action=cta, image_prompt=image_prompt)

    elif platform == "linkedin":
        cs = CreativeSet(
            platform=platform,
            headlines=[_truncate(f"{product} for {audience}", lim["headline"])],
            intro_text=_truncate(
                f"{audience.capitalize()}: see why teams choose {product}. "
                f"{vp[0]} and {vp[1].lower()}.", lim["intro_text"]),
            description=_truncate(f"{vp[0]}. {vp[2]}.", lim["description"]),
            call_to_action="Learn more", image_prompt=image_prompt)
    else:
        raise ValueError(f"unsupported platform: {platform}")

    return cs
