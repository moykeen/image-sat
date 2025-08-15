import hashlib
import json
import os
import shutil
from pathlib import Path

from .logic.segmentation import SegmentationModel


class DataStore:
    def __init__(self):
        top_work_dir = Path(os.environ["TOP_WORK_DIR"]).expanduser()
        workset = os.environ["WORKSET"]
        accepted = os.environ["ACCEPTED"]
        segmentation_model_path = os.environ["SEGMENTATION_MODEL"]

        self.workdir = top_work_dir / workset
        self.class_dir = top_work_dir / "classes.json"
        self.image_dir = self.workdir / "images"
        self.label_dir = self.workdir / "labels"
        self.accepted_image_dir = top_work_dir / accepted / "images"
        self.accepted_label_dir = top_work_dir / accepted / "labels"
        self.sam_dir = self.workdir / "sam"
        self.label_dir.mkdir(exist_ok=True)

        self.undo_history_dir = top_work_dir / "undo_history"
        self.undo_history_dir.mkdir(exist_ok=True)
        self.curr_undo_index = 0

        self.segmentation_model = (
            SegmentationModel(segmentation_model_path)
            if segmentation_model_path
            else None
        )

        self.current_image_path = None

    def load_id2color(self) -> dict:
        with open(self.class_dir, "r") as f:
            self.classes = json.loads("".join(f.readlines()))["classes"]
        ids = [c["id"] for c in self.classes]
        colors = [c["color"] for c in self.classes]
        return {k: v for k, v in zip(ids, colors)}

    def get_sorted_images(self):
        return sorted(self.image_dir.iterdir(), key=lambda p: p.stat().st_mtime)

    def get_current_label_path(self) -> Path:
        curr_label_path = self.label_dir / (self.current_image_path.stem + ".png")
        return curr_label_path

    def transfer_image_to_accept(self, label_saver):
        # get hash value  of the image
        with open(self.current_image_path, "rb") as f:
            bytes = f.read()
            hash_val = hashlib.md5(bytes).hexdigest()
            print("hash value:", hash_val)

        shutil.copy(
            self.current_image_path,
            self.accepted_image_dir / f"{hash_val}{self.current_image_path.suffix}",
        )

        label_path = self.accepted_label_dir / (hash_val + ".png")
        label_saver(label_path)

    def run_sam(self):
        if self.segmentation_model is None:
            raise ValueError
        print("SAM run button clicked")

        sam_path = self.sam_dir / (self.current_image_path.stem + ".png")
        self.segmentation_model.segment_image(self.current_image_path, sam_path)
        return sam_path

    def reset_undo_history(self):
        if self.undo_history_dir.exists():
            shutil.rmtree(self.undo_history_dir)
        self.undo_history_dir.mkdir(exist_ok=True)
        self.curr_undo_index = -1

    def save_undo_state(self):
        self.curr_undo_index += 1
        undo_file = self.undo_history_dir / f"undo_{self.curr_undo_index}.png"
        return undo_file

    def undo(self) -> Path | None:
        print("Undo operation triggered", self.curr_undo_index)
        if self.curr_undo_index > 0:
            self.curr_undo_index -= 1
            undo_file = self.undo_history_dir / f"undo_{self.curr_undo_index}.png"
            if undo_file.exists():
                return undo_file
        return None

    def redo(self) -> Path | None:
        redo_file = self.undo_history_dir / f"undo_{self.curr_undo_index + 1}.png"
        if redo_file.exists():
            self.curr_undo_index += 1
            return redo_file

        return None
