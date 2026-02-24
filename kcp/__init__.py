from kcp.nodes.asset_nodes import KCP_AssetPick, KCP_AssetSave
from kcp.nodes.keyframe_set_save import KCP_KeyframeSetSave
from kcp.nodes.keyframe_set_mark_picked import KCP_KeyframeSetMarkPicked
from kcp.nodes.keyframe_promote import KCP_KeyframePromoteToAsset
from kcp.nodes.keyframe_set_item_load import KCP_KeyframeSetItemLoad
from kcp.nodes.keyframe_set_item_save_image import KCP_KeyframeSetItemSaveImage
from kcp.nodes.project_init import KCP_ProjectInit
from kcp.nodes.project_status import KCP_ProjectStatus
from kcp.nodes.prompt_compose import KCP_PromptCompose
from kcp.nodes.stack_nodes import KCP_StackPick, KCP_StackSave
from kcp.nodes.variant_pack import KCP_VariantPack
from kcp.nodes.variant_pick import KCP_VariantPick

NODE_CLASS_MAPPINGS = {
    "KCP_ProjectInit": KCP_ProjectInit,
    "KCP_AssetSave": KCP_AssetSave,
    "KCP_AssetPick": KCP_AssetPick,
    "KCP_StackSave": KCP_StackSave,
    "KCP_StackPick": KCP_StackPick,
    "KCP_PromptCompose": KCP_PromptCompose,
    "KCP_VariantPack": KCP_VariantPack,
    "KCP_VariantPick": KCP_VariantPick,
    "KCP_ProjectStatus": KCP_ProjectStatus,
    "KCP_KeyframeSetSave": KCP_KeyframeSetSave,
    "KCP_KeyframeSetMarkPicked": KCP_KeyframeSetMarkPicked,
    "KCP_KeyframeSetItemSaveImage": KCP_KeyframeSetItemSaveImage,
    "KCP_KeyframeSetItemLoad": KCP_KeyframeSetItemLoad,
    "KCP_KeyframePromoteToAsset": KCP_KeyframePromoteToAsset,
    "KCP_ProjectStatus": KCP_ProjectStatus,
    "KCP_KeyframeSetSave": KCP_KeyframeSetSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {k: k for k in NODE_CLASS_MAPPINGS}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
