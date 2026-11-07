import re
import textwrap
from logging import getLogger
from pathlib import Path
from typing import TypedDict
from xml.sax.saxutils import escape

from ok_agent.utils import display_text


class SkillMetadataError(Exception):
    """Base Exception for SKILL metadata errors."""


class FrontmatterNotFoundError(SkillMetadataError):
    """Raised when frontmatter is missing."""


class MetadataValidationError(SkillMetadataError):
    """Raised when fields does not conform to the skills specification."""


class SkillMetadata(TypedDict):
    name: str
    description: str
    location: str
    disable_model_invocation: bool


logger = getLogger(__name__)


def read_skill_metadata(file: Path) -> SkillMetadata:
    """Returns parsed frontmatter.

    Args:
        path: Path to file having frontmatter.

    Raises:
        OSError: If fails to read the file.
        FrontmatterNotFoundError: If frontmatter is missing.
        MetadataValidationError: If fields does not conform to the skills specification.
    """
    disable_model_invocation = False

    name = None
    NAME_REGEX = re.compile(r'^[a-z0-9][a-z0-9-]{,62}[a-z0-9]$')

    EXCLUDE_SKILLS_FIELD = 'disable-model-invocation'

    description = None

    with open(file) as f:
        first_line = f.readline().strip()
        if not first_line.startswith('---'):
            raise FrontmatterNotFoundError('Frontmatter not found in file')

        for line in f:
            if line.strip() == '---':
                break

            if ':' not in line:
                continue

            field, _, value = line.partition(':')

            if field == 'name':
                name = value.strip().strip('"')
                if NAME_REGEX.match(name) is None:
                    raise MetadataValidationError(
                        'Validation failed: "name" must conform to: Max 64 characters. Lowercase letters, numbers, and hyphens only. Must not start or end with a hyphen'
                    )

            elif field == 'description':
                description = value.strip().strip('"')
                if not description or len(description) > 1024:
                    raise MetadataValidationError(
                        'Validation failed: "description" must conform to: Max 1024 characters. Non-empty'
                    )

            elif field == EXCLUDE_SKILLS_FIELD and value.strip() == 'true':
                disable_model_invocation = True

    if not name or not description:
        raise MetadataValidationError('Missing required fields')

    return {
        'name': name,
        'description': description,
        'location': str(file.resolve()),
        'disable_model_invocation': disable_model_invocation,
    }


def find_skills(path: Path) -> list[Path]:
    """Returns the list of skills found.

    Args: Path that contains the skill directories.

    Check for skills dir in the path and search skills at max depth of 1
    and returns list of path of the found SKILL.md files.
    """
    if not path.exists():
        return []

    SKILL = 'SKILL.md'

    return [
        entry / SKILL
        for entry in path.iterdir()
        if entry.is_dir() and (entry / SKILL).exists()
    ]


def get_skills() -> list[SkillMetadata]:
    """Returns a list of skill metadata."""

    skills = []
    SKILLS_DIRECTORY = 'skills'

    SKILL_SEARCH_PATHS = [
        '.ok',
        '.agents',
    ]

    search_paths: list[Path] = [Path(dir) for dir in SKILL_SEARCH_PATHS]
    search_paths.extend(Path.home() / dir for dir in SKILL_SEARCH_PATHS)

    skill_dirs = [
        entry / SKILLS_DIRECTORY
        for entry in search_paths
        if entry.is_dir() and (entry / SKILLS_DIRECTORY).exists()
    ]

    for path in skill_dirs:
        skills_files = find_skills(path)

        for file in skills_files:
            try:
                skills.append(read_skill_metadata(file))

            except OSError as e:
                logger.exception(f"Failed to read skill: '{file}'")
                display_text(f'Ignoring skill "{file}": {e}', style='ERROR')

            except SkillMetadataError as e:
                logger.error(e)
                display_text(f'Ignoring skill "{file}": {e}', style='ERROR')

    return skills


def skills_to_xml(skills: list[SkillMetadata]) -> str | None:
    """Returns formatted skills for the system prompt.

    Args: List of skill metadata.
    """
    skills_available = [
        skill for skill in skills if not skill['disable_model_invocation']
    ]

    if len(skills_available) == 0:
        return None

    skills_available.sort(key=lambda skill: skill['name'])

    lines: list[str] = ['You have access to the following skills:']

    lines.append('<skills>')
    for skill in skills_available:
        name = escape(skill['name'])
        location = skill['location']
        description = escape(skill['description'])

        lines.append('  <skill>')
        lines.append(f'    <name>{name}</name>')
        lines.append(f'    <description>{description}</description>')
        lines.append(f'    <location>{location}</location>')
        lines.append('  </skill>')
    lines.append('</skills>')
    lines.append(
        textwrap.dedent("""

            Skills provide instructions on what to do and how to behave when performing specific tasks.
            - You MUST read the relevant skill and follow its instruction when the task aligns with the skill's description.
            - Also read the skill when the user explicitly requests it using /skill:{name}.
            """)
    )

    return '\n'.join(lines)
