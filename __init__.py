from .nodes import SmartTileRefine

NODE_CLASS_MAPPINGS = {"SmartTileRefine": SmartTileRefine}
NODE_DISPLAY_NAME_MAPPINGS = {"SmartTileRefine": "Tile Refine"}
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
