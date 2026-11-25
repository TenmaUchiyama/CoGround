using UnityEngine;

public class LookAtCamera : MonoBehaviour
{
    // Start is called once before the first execution of Update after the MonoBehaviour is created

    private Camera mainCamera;
    void Start()
    {
        mainCamera = GameObject.FindGameObjectWithTag("main camera").GetComponent<Camera>();
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}
