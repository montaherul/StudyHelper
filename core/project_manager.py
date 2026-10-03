"""
Project manager orchestrating project directories, manifests, and database synchronization.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from config.settings import settings
from database.db import db
from database.models import Project
from utils.filesystem import sanitize_filename, ensure_dir
from utils.logger import logger


class ProjectManager:
    """Manages project creation, folder scaffolding, manifest persistence, and discovery."""

    def __init__(self):
        self.db = db

    def create_project(
        self,
        name: str,
        subject: str = "",
        course: str = "",
        teacher: str = "",
        semester: str = "",
        description: str = "",
        custom_output_dir: Optional[str] = None
    ) -> Project:
        """
        Creates a new project, scaffolds standard directories, writes project.json,
        and persists the record to the SQLite database.
        """
        project_id = str(uuid.uuid4())
        safe_name = sanitize_filename(name)
        
        try:
            base_dir = Path(custom_output_dir) if custom_output_dir else Path(settings.get("projects_dir"))
            ensure_dir(base_dir)
        except Exception:
            import tempfile
            base_dir = Path(tempfile.gettempdir()) / "LocalStudy_Projects"
            ensure_dir(base_dir)

        project_dir = base_dir / safe_name
        
        # If directory already exists, append unique suffix
        if project_dir.exists():
            project_dir = base_dir / f"{safe_name}_{project_id[:6]}"

        # Scaffold standard folders
        ensure_dir(project_dir / "source")
        ensure_dir(project_dir / "screenshots")
        ensure_dir(project_dir / "transcript")
        ensure_dir(project_dir / "pdf")
        ensure_dir(project_dir / "metadata")
        ensure_dir(project_dir / "logs")

        now_str = datetime.now().isoformat()
        project = Project(
            id=project_id,
            name=name,
            subject=subject,
            course=course,
            teacher=teacher,
            semester=semester,
            description=description,
            output_path=str(project_dir),
            created_at=now_str,
            updated_at=now_str
        )

        # Write manifest file
        self.save_manifest(project)

        # Save to database
        self.db.save_project(project)
        logger.info(f"Created project '{name}' at {project_dir}")
        return project

    def save_manifest(self, project: Project) -> None:
        """Saves project.json manifest into the project root directory."""
        manifest_path = Path(project.output_path) / "project.json"
        manifest_data = {
            "id": project.id,
            "name": project.name,
            "subject": project.subject,
            "course": project.course,
            "teacher": project.teacher,
            "semester": project.semester,
            "description": project.description,
            "output_path": project.output_path,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=4)

    def load_project_by_id(self, project_id: str) -> Optional[Project]:
        """Retrieves project from database."""
        return self.db.get_project(project_id)

    def load_project_from_directory(self, dir_path: Path | str) -> Optional[Project]:
        """Loads a project from an existing directory containing project.json."""
        manifest_path = Path(dir_path) / "project.json"
        if not manifest_path.exists():
            return None
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["output_path"] = str(Path(dir_path).resolve())
            project = Project(**data)
            # Sync to local database
            self.db.save_project(project)
            return project
        except Exception as e:
            logger.error(f"Failed to load project from {dir_path}: {e}")
            return None

    def list_recent_projects(self, limit: int = 20) -> List[Project]:
        """Returns recent projects from SQLite database."""
        return self.db.list_projects(limit=limit)

    def list_all_projects(self, limit: int = 100) -> List[Project]:
        """Returns all projects from database."""
        return self.db.list_projects(limit=limit)

    def delete_project(self, project_id: str, delete_files: bool = False) -> None:
        """Deletes project from database and optionally removes files from disk."""
        project = self.db.get_project(project_id)
        if project and delete_files:
            import shutil
            proj_dir = Path(project.output_path)
            if proj_dir.exists():
                shutil.rmtree(proj_dir, ignore_errors=True)
        self.db.delete_project(project_id)
        logger.info(f"Deleted project ID {project_id}")


project_manager = ProjectManager()
