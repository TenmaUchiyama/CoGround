using Oculus.Interaction;
using Oculus.Interaction.OVR.Editor.QuickActions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// メニュー CoGround > VR で箱のゴーストをつかめるようにする
///   1. distance grab の interactor が無ければ、OVRCameraRig + OVRComprehensiveInteractionRig を追加する
///      (ISDK の「Add OVR Interaction Rig」と同じ。位置・向きは今の Main Camera の足元に合わせ、Main Camera は無効にする)
///   2. 運べる箱 (MoveItPickable) すべてに MoveItGhostDistanceGrab を付ける
/// </summary>
public static class GhostDistanceGrabSetup
{
    [MenuItem("CoGround/VR で箱のゴーストをつかめるようにする")]
    static void Setup()
    {
        Debug.Log("Starting GDGS");
        if (Object.FindAnyObjectByType<DistanceGrabInteractor>(FindObjectsInactive.Include) == null)
        {
            Camera oldCamera = FindNonXrMainCamera();
            OVRQuickActionsAPI.AddOVRInteractionRig(generateAsEditableCopy: false);

            var rig = Object.FindAnyObjectByType<OVRCameraRig>();
            if (rig != null && oldCamera != null)
            {
                Undo.RecordObject(rig.transform, "Place OVRCameraRig");
                Vector3 p = oldCamera.transform.position;
                Vector3 fwd = Vector3.ProjectOnPlane(oldCamera.transform.forward, Vector3.up);
                rig.transform.SetPositionAndRotation(new Vector3(p.x, 0f, p.z),
                    fwd.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(fwd, Vector3.up) : Quaternion.identity);

                Undo.RecordObject(oldCamera.gameObject, "Disable Main Camera");
                oldCamera.gameObject.SetActive(false);
            }
            Debug.Log("[GhostDistanceGrabSetup] OVRCameraRig + OVRComprehensiveInteractionRig を追加した");
        }

        int added = 0;
        foreach (var pickable in Object.FindObjectsByType<MoveItPickable>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (pickable.GetComponent<MoveItGhostDistanceGrab>() != null) continue;
            Undo.AddComponent<MoveItGhostDistanceGrab>(pickable.gameObject);
            added++;
        }

        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        Debug.Log($"[GhostDistanceGrabSetup] MoveItGhostDistanceGrab を {added} 個の箱に付けた。シーンを保存してから Play する");
    }

    static Camera FindNonXrMainCamera()
    {
        foreach (var cam in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None))
        {
            if (cam.GetComponentInParent<OVRCameraRig>() == null && cam.CompareTag("MainCamera")) return cam;
        }
        return null;
    }
}
