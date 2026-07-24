from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PrereleaseType(Enum):
    ALPHA = "alpha"
    BETA = "beta"
    RC = "rc"
    STABLE = ""

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, s: str) -> PrereleaseType:
        mapping = {
            "alpha": cls.ALPHA,
            "a": cls.ALPHA,
            "beta": cls.BETA,
            "b": cls.BETA,
            "rc": cls.RC,
            "release-candidate": cls.RC,
            "stable": cls.STABLE,
            "release": cls.STABLE,
        }
        return mapping.get(s.strip().lower(), cls.ALPHA)


@dataclass
class Version:
    major: int = 4
    minor: int = 0
    patch: int = 0
    prerelease: PrereleaseType = PrereleaseType.ALPHA
    prerelease_number: int = 1

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease != PrereleaseType.STABLE:
            return f"{base}-{self.prerelease.value}.{self.prerelease_number}"
        return base

    def tag(self) -> str:
        return f"v{self}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
            and self.prerelease_number == other.prerelease_number
        )

    def __lt__(self, other: Version) -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        order = {PrereleaseType.ALPHA: 0, PrereleaseType.BETA: 1, PrereleaseType.RC: 2, PrereleaseType.STABLE: 3}
        if self.prerelease != other.prerelease:
            return order.get(self.prerelease, 0) < order.get(other.prerelease, 0)
        return self.prerelease_number < other.prerelease_number


SEMVER_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>alpha|beta|rc)\.?(?P<number>\d+)?)?$",
    re.IGNORECASE,
)


class VersionManager:
    def __init__(self, version_string: Optional[str] = None):
        if version_string:
            self.current = self.parse(version_string)
        else:
            self.current = Version()

    @staticmethod
    def parse(s: str) -> Version:
        m = SEMVER_RE.match(s.strip())
        if not m:
            raise ValueError(f"Invalid semver string: {s!r}")
        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        prerelease_str = m.group("prerelease")
        prerelease = PrereleaseType.from_string(prerelease_str) if prerelease_str else PrereleaseType.STABLE
        number_str = m.group("number")
        prerelease_number = int(number_str) if number_str else 1
        return Version(major, minor, patch, prerelease, prerelease_number)

    @staticmethod
    def from_tag(tag: str) -> Version:
        return VersionManager.parse(tag)

    def bump_alpha(self, name: str = "") -> Version:
        if self.current.prerelease == PrereleaseType.ALPHA:
            self.current.prerelease_number += 1
        else:
            self.current.prerelease = PrereleaseType.ALPHA
            self.current.prerelease_number = 1
        return self.current

    def bump_beta(self, name: str = "") -> Version:
        self.current.prerelease = PrereleaseType.BETA
        self.current.prerelease_number = 1
        return self.current

    def bump_rc(self, name: str = "") -> Version:
        self.current.prerelease = PrereleaseType.RC
        self.current.prerelease_number = 1
        return self.current

    def bump_stable(self, name: str = "") -> Version:
        self.current.prerelease = PrereleaseType.STABLE
        self.current.prerelease_number = 0
        return self.current

    def bump_major(self, name: str = "") -> Version:
        self.current.major += 1
        self.current.minor = 0
        self.current.patch = 0
        self.current.prerelease = PrereleaseType.STABLE
        self.current.prerelease_number = 0
        return self.current

    def bump_minor(self, name: str = "") -> Version:
        self.current.minor += 1
        self.current.patch = 0
        self.current.prerelease = PrereleaseType.STABLE
        self.current.prerelease_number = 0
        return self.current

    def bump_patch(self, name: str = "") -> Version:
        self.current.patch += 1
        self.current.prerelease = PrereleaseType.STABLE
        self.current.prerelease_number = 0
        return self.current

    def __str__(self) -> str:
        return str(self.current)

    def __repr__(self) -> str:
        return f"VersionManager({self.current})"