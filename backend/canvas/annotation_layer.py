from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnnotationLayer:
  annotations:list = field(default_factory=list)
  active_tool:str | None = None
  selected_color:str = "#FFFF00"

  def add_annotation(self, annotation) -> None:
    self.annotations.append(annotation)
    logger.info(f"Added annotation:{annotation.annotation_type} on page {annotation.page_number}")

  def remove_annotation(self, annotation_id:str) -> bool:
    for i, ann in enumerate(self.annotations):
      if ann.id == annotation_id:
        self.annotations.pop(i)
        logger.info(f"Removed annotation:{annotation_id}")
        return True
    return False

  def clear_annotations(self) -> None:
    self.annotations.clear()
    logger.info("Cleared all annotations")

  def get_annotations_on_page(self, page_num:int) -> list:
    return [a for a in self.annotations if a.page_number == page_num]

  def get_annotations_by_type(self, annotation_type:str) -> list:
    return [a for a in self.annotations if a.annotation_type == annotation_type]

  def set_active_tool(self, tool:str | None) -> None:
    self.active_tool = tool
    logger.debug(f"Active tool set to:{tool}")

  def set_color(self, color:str) -> None:
    self.selected_color = color

  def export_annotations(self) -> list[dict]:
    return [
      {
        "id":ann.id,
        "page":ann.page_number,
        "type":ann.annotation_type,
        "color":ann.color,
        "coordinates":ann.coordinates,
        "content":ann.content,
        "formula_ref":ann.formula_reference,
        "step_ref":ann.step_reference
      }
      for ann in self.annotations
    ]

  def import_annotations(self, annotations_data:list[dict]) -> int:
    from backend.math_wizard.annotator import Annotation

    count = 0
    for data in annotations_data:
      annotation = Annotation(
        id=data.get("id", ""),
        page_number=data.get("page", 1),
        annotation_type=data.get("type", "highlight"),
        color=data.get("color", "#FFFF00"),
        coordinates=tuple(data.get("coordinates", (0, 0, 100, 20))),
        content=data.get("content", ""),
        formula_reference=data.get("formula_ref"),
        step_reference=data.get("step_ref")
      )
      self.add_annotation(annotation)
      count += 1

    return count
