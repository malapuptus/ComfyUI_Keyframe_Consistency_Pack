from kcp.nodes.asset_nodes import KCP_AssetPick, KCP_AssetSave
from kcp.nodes.keyframe_set_save import KCP_KeyframeSetSave
from kcp.nodes.keyframe_set_mark_picked import KCP_KeyframeSetMarkPicked
from kcp.nodes.keyframe_set_pick import KCP_KeyframeSetPick
from kcp.nodes.keyframe_promote import KCP_KeyframePromoteToAsset
from kcp.nodes.keyframe_set_item_load import KCP_KeyframeSetItemLoad
from kcp.nodes.keyframe_set_item_pick import KCP_KeyframeSetItemPick
from kcp.nodes.keyframe_set_load_batch import KCP_KeyframeSetLoadBatch
from kcp.nodes.keyframe_set_summary import KCP_KeyframeSetSummary
from kcp.nodes.render_pack_status import KCP_RenderPackStatus
from kcp.nodes.keyframe_set_item_save_image import KCP_KeyframeSetItemSaveImage
from kcp.nodes.keyframe_set_item_save_batch import KCP_KeyframeSetItemSaveBatch
from kcp.nodes.project_init import KCP_ProjectInit
from kcp.nodes.project_status import KCP_ProjectStatus
from kcp.nodes.prompt_compose import KCP_PromptCompose
from kcp.nodes.character_forge import KCP_CharacterForge
from kcp.nodes.environment_forge import KCP_EnvironmentForge
from kcp.nodes.stack_nodes import KCP_StackPick, KCP_StackSave
from kcp.nodes.variant_pack import KCP_VariantPack
from kcp.nodes.variant_pick import KCP_VariantPick
from kcp.nodes.variant_unroll import KCP_VariantUnroll

NODE_CLASS_MAPPINGS = {
    "KCP_ProjectInit": KCP_ProjectInit,
    "KCP_AssetSave": KCP_AssetSave,
    "KCP_AssetPick": KCP_AssetPick,
    "KCP_StackSave": KCP_StackSave,
    "KCP_StackPick": KCP_StackPick,
    "KCP_PromptCompose": KCP_PromptCompose,
    "KCP_CharacterForge": KCP_CharacterForge,
    "KCP_EnvironmentForge": KCP_EnvironmentForge,
    "KCP_VariantPack": KCP_VariantPack,
    "KCP_VariantPick": KCP_VariantPick,
    "KCP_VariantUnroll": KCP_VariantUnroll,
    "KCP_ProjectStatus": KCP_ProjectStatus,
    "KCP_KeyframeSetSave": KCP_KeyframeSetSave,
    "KCP_KeyframeSetMarkPicked": KCP_KeyframeSetMarkPicked,
    "KCP_KeyframeSetPick": KCP_KeyframeSetPick,
    "KCP_KeyframeSetItemSaveImage": KCP_KeyframeSetItemSaveImage,
    "KCP_KeyframeSetItemSaveBatch": KCP_KeyframeSetItemSaveBatch,
    "KCP_KeyframeSetItemLoad": KCP_KeyframeSetItemLoad,
    "KCP_KeyframeSetItemPick": KCP_KeyframeSetItemPick,
    "KCP_KeyframeSetLoadBatch": KCP_KeyframeSetLoadBatch,
    "KCP_KeyframeSetSummary": KCP_KeyframeSetSummary,
    "KCP_RenderPackStatus": KCP_RenderPackStatus,
    "KCP_KeyframePromoteToAsset": KCP_KeyframePromoteToAsset,
}

NODE_DISPLAY_NAME_MAPPINGS = {k: k for k in NODE_CLASS_MAPPINGS}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
