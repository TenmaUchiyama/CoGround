# Diminished Reality Quickstart（メッシュ + ステンシルマスク）

実物の上に「物が無いときの背景メッシュ」を重ねて、物を消したように見せるやり方。
動作するサンプル: `Assets/Main/Scene/Test/SplatTest/SplatTest.unity`

## しくみ

```
① DR_MaskBox (DR/StencilMask)          ← 透明な箱。色も深度も描かず、覆った画素のステンシルに 1 を書くだけ
        ↓ Queue: Geometry-10（先に描く）
② 背景メッシュ (DR/StencilReadTextured) ← スキャンした部屋/机。ステンシル == 1 の画素にだけ描かれる
        ↓ Queue: Geometry+10（後に描く）
③ それ以外の画素                         ← 何も描かれないのでパススルーのまま
```

結果: 箱の中だけ「物が無い背景」が見え、そこにある実物が消えたように見える。
箱を消したい物にかぶせれば消える。箱は `DRMaskFollowDetection` が物体検出の結果に合わせて自動で動かす。

## 使うファイル

| 種類 | パス | 役割 |
|---|---|---|
| シェーダー | `Assets/Main/Material/DiminishReality/Resources/DR_StencilMask.shader` | マスク（ステンシルに書くだけ）。実行中に箱を作るスクリプトが読めるように Resources に置いている |
| シェーダー | `Assets/Main/Material/DiminishReality/DR_StencilReadTextured.shader` | 背景メッシュ用（テクスチャ、ライティングなし） |
| シェーダー | `Assets/Main/Material/DiminishReality/DR_StencilReadUnlit.shader` | 単色。マスクの動作確認用 |
| マテリアル | `Assets/Main/Material/DiminishReality/DR_StencilMask.mat` | 箱に付ける |
| マテリアル | `Assets/Main/Material/DiminishReality/DR_StencilReadUnlit.mat` | 確認用の単色（灰色） |
| マテリアル | `Assets/Main/Model/TestHouse/main.mat` | 背景メッシュの例（DR/StencilReadTextured + スキャンのテクスチャ） |
| スクリプト | `Assets/Main/Script/DiminishReality/DRMaskFollowDetection.cs` | 検出した物に箱を合わせる |
| スクリプト | `Assets/Main/Script/Detection/DetectionPipeline.cs` | 2D 検出 → 3D の箱、追跡、固定（エージェントの隣に自動で追加される） |

## 手順

### 1. シーンの土台

Meta の Building Blocks から追加する:

- `[BuildingBlock] Camera Rig`
- `[BuildingBlock] Passthrough`
- 検出で箱を動かす場合: `[BuildingBlock] Passthrough Camera Access` と `[BuildingBlock] Object Detection`

### 2. 背景メッシュを用意する

1. 消したい物を**どけた状態**で、部屋や机をスキャンする（Scaniverse などで、テクスチャ付きの FBX/OBJ を書き出す）。
2. `Assets/Main/Model/<名前>/` に入れる。
3. マテリアルを作る（または既存のものを使う）:
   - Shader: **`DR/StencilReadTextured`**
   - Texture: スキャンのテクスチャ
   - Stencil Ref: **1**（マスクと同じ値）
4. シーンに置いて、モデルの全マテリアルをこれにする。

### 2b. 背景をガウシアンスプラットにする（メッシュの代わり）

メッシュの代わりに、SplatXR のスプラットを背景にできる。マスクの箱・検出・After 表示はそのまま使える。

1. 消したい物を**どけた状態**でスキャンし、`.ply` にする（`.spz` なら SuperSplat か `npx @playcanvas/splat-transform in.spz out.ply` で変換）。
   - 軽くする: `npx @playcanvas/splat-transform in.ply -H 0 out.ply`（SH を 0 に）。SplatXR の目安はシーン全体で **20 万点以下**。DR では箱の周りしか見えないので、`-B`（箱）で物の周りだけ切り出すと大きく減らせる。
2. **SplatXR > Building Blocks Panel → Splat Renderer** で `.ply` を指定して Add to Scene。
3. 作られたマテリアル（`Assets/Materials/SplatMaterials/SplatMaterial_<名前>.mat`）の Shader を **`DR/StencilReadSplat`** にする。Stencil Ref は **1**。
4. 位置合わせは手順 3 と同じ。合わせる間は Shader を `SplatXR/SplatShader` に戻すと全体が見える。

| 項目 | 初期値 | 効果 |
|---|---|---|
| Feather Width (m) | 0.03 | メッシュ版と同じ（`DRMaskShaderGlobals` が必要） |
| Alpha Dst Blend | OneMinusSrcAlpha | スキャンが薄い所で実物が透けるときは **One** にする（どこでもパススルーを隠す。薄い所は少し暗くなる） |
| Grain | 0.03 | パススルーのノイズに合わせる |
| Brightness など / ASC-CDL | SplatXR と同じ | 色合わせ。`SplatPassthroughColorAdjustment` で ASC-CDL を自動で求めることもできる |

- **右手の箱で消す（DRHandMask）**: スプラットを `Splat Align`（Splat Offset Placer の Target）の子に入れて、メニュー **CoGround > DR 右手マスクを配置** を実行する。Target の下にスプラットがあれば、背景はスプラットになる（マテリアルは実行中に `DR/StencilReadSplat` の複製を作るので、手順 3 の差し替えは不要）。Feather / Grain / 透け防止は `DRHandMask` の「スプラットの DR」で変える。右スティック押し込みで ON / OFF、OFF のときスプラットは出ない（Splat Offset Placer で動かしている間だけ全体が出る）。
- スプラットは当たり判定を持たないので、検出のレイを当てる場合は、別に MeshCollider 用の簡単なメッシュ（床・机の Plane など）を置く。

### 3. 背景メッシュを現実に合わせる（いちばん大事）

- 今は**手で合わせている**。実機（または Link）で見ながら、Transform の位置・回転を調整する（SplatTest の `House` は Y 回転 約 -209°）。
- 合わせるときは、一時的にマテリアルを普通のシェーダー（Unlit/Texture など）にすると、全体が見えて合わせやすい。終わったら `DR/StencilReadTextured` に戻す。
- ずれていると、箱の中の背景が実物とずれて見える。消えて見えるかどうかは、ほぼここで決まる。
- 検出の 3D 化でレイを当てたい場合は、背景メッシュに **MeshCollider** を付ける（環境の深度が使えないときに、このコライダーに当てて位置を求める）。

### 4. マスクの箱を置く

1. `3D Object > Cube` を作り、名前を `DR_MaskBox` にする。
2. マテリアルを **`DR_StencilMask.mat`** にする。
3. **BoxCollider は外す**（検出のレイが箱に当たらないように。スクリプトでも除外しているが、無い方が安全）。
4. 手で消すなら、消したい物にかぶせて大きさを合わせて終わり。

### 5. 動作確認（背景メッシュの前に）

背景メッシュの代わりに、`DR_StencilReadUnlit.mat` を付けた大きめの Plane などを置いて再生する。
**箱の中だけ灰色、外はパススルー**になればマスクは動いている。確認できたら外す。

### 6. 検出で箱を自動で動かす（任意）

1. 空の GameObject（例: `FollowDetection`）に **`DRMaskFollowDetection`** を付ける。
2. Inspector:

| 項目 | 設定 | SplatTest の値 |
|---|---|---|
| Agent | `[BuildingBlock] Object Detection` の ObjectDetectionAgent（空なら自動で探す） | — |
| Pipeline | 空でよい（エージェントの隣に自動で追加される） | — |
| Target Label | 消したい物のクラス名（`Assets/MetaXR/class_labels.txt`） | `keyboard` |
| Raycast Layers | 背景メッシュの MeshCollider が入っているレイヤー | Everything |
| Mask Box | `DR_MaskBox` | — |
| Hide Until Detected | 見つかるまで箱を消す | ON |
| Size Margin | 検出した大きさに対する余裕 | 1.2 |
| Min Depth | 箱の奥行きの最小値 (m) | 0.2 |
| Extent Below / Above | 物の下 / 上にはみ出す量 (m)。下は机にめり込ませる | 0.05 / 0.04 |

3. 再生すると、対象が見つかったら箱がそこに移動し、安定すると固定される（ログ: `Following ...` → `Mask locked ...`）。
4. 物を動かしたあとは `ResetMask()` を呼ぶと、また追いかける。
5. 平滑化や固定までの時間は、`DetectionPipeline` コンポーネントの「追跡・平滑化・固定」で変える。

### 7. なじませる（背景マテリアルの調整）

`DR/StencilReadTextured` のマテリアル（例: `Model/TestHouse/main.mat`）で調整する。

| 項目 | 初期値 | 効果 |
|---|---|---|
| Feather Width (m) | 0.03 | 箱の輪郭に近いほど透明にして、パススルーと混ぜる。0 で無効（くっきり切れる） |
| Blur (mip bias) | 1 | 背景を少しぼかす。パススルーはスキャンより柔らかいので合わせる |
| Grain | 0.03 | 毎フレーム変わるざらつき。パススルーのノイズに合わせる |
| Brightness / Contrast / Saturation | 1 / 1 / 1 | パススルーとの色の差を詰める（Tint と組み合わせて使う） |

- Feather には、箱の位置をシェーダーに渡す **`DRMaskShaderGlobals`** が箱に付いている必要がある。`DRMaskFollowDetection` を使っていれば自動で付く。手で箱を置く場合は自分で付ける。無いときは Feather は効かない（従来どおり）。
- 縁は箱の余白部分で混ざる。余白が小さいと物の端まで透けるので、Feather Width は Size Margin による余白より小さくする。
- 消した物の**影**が箱の外に残るときは、Size Margin を大きくして影まで覆う。
- Feather が効く箱は同時に 8 個まで。9 個以上あると Feather は切れる（くっきり切れるが、消えはする）。

### 8. Plan で動く物を消す（After 表示）

`CoGroundAfterView` の **Diminish Style** を `DiminishedReality`（初期値）にすると、After で「動く物」の元の位置に
マスクの箱が自動で置かれる（`DR Mask (<物体 ID>)`。Before に戻すと消える）。

- 箱の位置と大きさは、シーンの物体（`CoGroundSceneObject`）ならその箱、カメラで認識した物体（`CoGroundPerceivedObjects`）なら認識結果の箱。
- 大きさは `DR Mask Margin`（倍率、初期値 1.2）と `DR Mask Padding`（各方向に足す量、初期値 0.02 m）で広げる。影が残るときは大きくする。
- 背景メッシュ（手順 2・3）がシーンに無いと DR では何も出ないので、そのときは `Ghost`（薄い姿を残す）で見せ、警告を 1 回出す。
- 箱の材質は空でよい（Resources の `DR_StencilMask` シェーダーから作る）。Stencil Ref を 1 以外にしているときだけ `DR Mask Material` に入れる。

## うまくいかないとき

| 症状 | 確認すること |
|---|---|
| 何も消えない（背景が出ない） | 背景メッシュのマテリアルが `DR/StencilReadTextured` か。マスクと背景の **Stencil Ref が同じ**か。箱が物にかぶっているか |
| 背景メッシュが全部見えてしまう | 背景が普通のシェーダーのまま。`DR/StencilReadTextured` に戻す |
| 箱が見える（灰色や白の箱） | 箱のマテリアルが `DR_StencilMask.mat` になっていない |
| 背景が実物とずれる | 手順 3 の位置合わせ。スキャンのスケールが合っているかも確認 |
| 箱が出てこない | Target Label がクラス名と合っているか。ログに `Ready.` が出ているか（出ていなければ Agent / Mask Box が未設定） |
| 箱の位置がおかしい | 環境の深度が取れていない可能性。背景メッシュに MeshCollider を付け、Raycast Layers に含める |
| 消した部分の色が浮く | スキャンの色が実際と違う。マテリアルの Tint で合わせる |