using Meta.XR;
using UnityEngine;
using UnityEngine.UI;

public class CaptureRGB : MonoBehaviour
{
    [SerializeField] PassthroughCameraAccess _cameraAccess;

    [SerializeField] RawImage rawImage;


    public void onTrigger() 
    {
        rawImage.texture = _cameraAccess.GetTexture();
    }
}
