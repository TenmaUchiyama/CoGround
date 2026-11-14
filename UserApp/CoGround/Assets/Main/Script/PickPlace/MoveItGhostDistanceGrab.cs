using Oculus.Interaction;
using Oculus.Interaction.Grab;
using Oculus.Interaction.GrabAPI;
using Oculus.Interaction.HandGrab;
using UnityEngine;

/// <summary>
/// MoveItPickable のゴーストを Meta XR Interaction SDK の distance grab でつかめるようにする。
/// 離すと、そこへロボットが箱を運ぶ (MoveItPickable.ReleaseGhost)。
///
/// 運べる箱 (MoveItPickable) と同じ GameObject に付ける。ゴーストは実行時に作られるので、
/// つかむためのコンポーネントも実行時に足す:
///   ゴースト: Rigidbody (kinematic) + Grabbable
///   └ DistanceGrab: DistanceGrabInteractable (コントローラ) + DistanceHandGrabInteractable (ハンド) + 動き方
/// シーンには OVRComprehensiveInteractionRig (distance grab の interactor) が必要
/// (メニュー CoGround > VR で箱のゴーストをつかめるようにする)。
/// </summary>
[RequireComponent(typeof(MoveItPickable))]
public class MoveItGhostDistanceGrab : MonoBehaviour
{
    [Tooltip("オン: つかむと手元へ引き寄せる (Building Block の既定)。" +
             "オフ: 離れたまま手の動きに合わせて動く (机の上の置き場所を遠くから指定しやすい)")]
    [SerializeField] bool pullToHand = false;
    [Tooltip("ハンドでつかむジェスチャー")]
    [SerializeField] GrabTypeFlags handGrabTypes = GrabTypeFlags.All;

    MoveItPickable pickable;
    Grabbable grabbable;
    bool held;

    void Awake() => pickable = GetComponent<MoveItPickable>();

    void Update()
    {
        // ゴーストは MoveItPickable.Start で作られる (Start の順番は決まっていないので、できるのを待つ)
        if (grabbable == null && pickable.Ghost != null) Setup(pickable.Ghost);
    }

    void Setup(Transform ghost)
    {
        var rb = ghost.GetComponent<Rigidbody>();
        if (rb == null) rb = ghost.gameObject.AddComponent<Rigidbody>();
        rb.isKinematic = true;
        rb.useGravity = false;

        // ISDK のコンポーネントは Start で設定を確かめるので、無効のまま足して設定してから有効にする
        bool wasActive = ghost.gameObject.activeSelf;
        ghost.gameObject.SetActive(false);

        grabbable = ghost.GetComponent<Grabbable>();
        if (grabbable == null) grabbable = ghost.gameObject.AddComponent<Grabbable>();
        grabbable.InjectOptionalRigidbody(rb);
        grabbable.InjectOptionalThrowWhenUnselected(false); // 離した場所に止める

        var child = new GameObject("DistanceGrab");
        child.transform.SetParent(ghost, false);

        IMovementProvider movement;
        if (pullToHand)
        {
            var toHand = child.AddComponent<MoveTowardsTargetProvider>();
            toHand.InjectTravellingData(PoseTravelData.FAST); // 0.1 秒で手元へ寄せる
            movement = toHand;
        }
        else
        {
            movement = child.AddComponent<MoveFromTargetProvider>();
        }

        var controllerGrab = child.AddComponent<DistanceGrabInteractable>();
        controllerGrab.InjectRigidbody(rb);
        controllerGrab.InjectOptionalPointableElement(grabbable);
        controllerGrab.InjectOptionalMovementProvider(movement);

        var handGrab = child.AddComponent<DistanceHandGrabInteractable>();
        handGrab.InjectAllDistanceHandGrabInteractable(handGrabTypes, rb,
            GrabbingRule.DefaultPinchRule, GrabbingRule.DefaultPalmRule);
        handGrab.InjectOptionalPointableElement(grabbable);
        handGrab.InjectOptionalMovementProvider(movement);

        ghost.gameObject.SetActive(wasActive);
        grabbable.WhenPointerEventRaised += OnPointerEvent;
    }

    void OnPointerEvent(PointerEvent evt)
    {
        bool nowHeld = grabbable.SelectingPointsCount > 0;
        if (nowHeld == held) return;
        held = nowHeld;
        if (held) pickable.HoldGhost();
        else pickable.ReleaseGhost();
    }

    void OnDestroy()
    {
        if (grabbable != null) grabbable.WhenPointerEventRaised -= OnPointerEvent;
    }
}
