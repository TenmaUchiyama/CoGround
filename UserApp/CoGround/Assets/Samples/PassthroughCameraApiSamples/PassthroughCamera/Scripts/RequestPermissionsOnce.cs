// Copyright (c) Meta Platforms, Inc. and affiliates.

using UnityEngine;
using UnityEngine.SceneManagement;

namespace PassthroughCameraSamples
{
    internal static class RequestPermissionsOnce
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void AfterSceneLoad()
        {
            // CoGround: シーンにすでにパススルー (Building Block など) があるときは足さない。
            // 2 つになると二重に重なって見える (Link では 2 つ目が捨てられる警告も出る)
            if (Object.FindAnyObjectByType<OVRPassthroughLayer>(FindObjectsInactive.Include) == null)
            {
                var ptLayerGo = new GameObject(nameof(OVRPassthroughLayer));
                Object.DontDestroyOnLoad(ptLayerGo);
                ptLayerGo.AddComponent<OVRPassthroughLayer>();
            }

            bool permissionsRequestedOnce = false;
            SceneManager.sceneLoaded += (scene, _) =>
            {
                if (scene.name != "StartScene")
                {
                    if (!permissionsRequestedOnce)
                    {
                        permissionsRequestedOnce = true;
                        OVRPermissionsRequester.Request(new[]
                        {
                            OVRPermissionsRequester.Permission.Scene,
                            OVRPermissionsRequester.Permission.PassthroughCameraAccess
                        });
                    }
                }
            };
        }
    }
}
