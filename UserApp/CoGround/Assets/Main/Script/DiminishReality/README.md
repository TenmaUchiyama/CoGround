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
| シェーダー | `Assets/Main/Material/DiminishReality/DR_StencilMask.shader` | マスク（ステンシルに書くだけ） |
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
- 箱は 1 つだけ対応（値がグローバルなため）。

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