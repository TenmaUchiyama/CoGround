from __future__ import annotations

from typing import Any

from ..rpc import RequestContext, Router
from ..state import SceneSnapshot

router = Router()


@router.method(
    "scene.update",
    params=SceneSnapshot,
    description="シーン全体（物体と領域）を置き換える。全クライアントに state.updated が届く",
)
async def update_scene(ctx: RequestContext, scene: SceneSnapshot) -> dict[str, Any]:
    version = ctx.services.state.set_scene(scene)
    # TODO: ここで Plan を作り直す（ルール照合 → 目標 → 置き位置 → 順序 → 動作計画）
    await ctx.services.publish_state()
    return {"version": version, "objects": len(scene.objects), "regions": len(scene.regions)}
