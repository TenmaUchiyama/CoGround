using System.Collections;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// Quest コントローラのトリガー (人差し指) を押している間 PushToTalkTranscriber で録音する。
/// エディタ / PC 用にスペースキーでも同じ操作ができる。
/// 押した瞬間と離した瞬間にコントローラを短く振動させる。
/// </summary>
[RequireComponent(typeof(PushToTalkTranscriber))]
public class PushToTalkControllerInput : MonoBehaviour
{
    public enum Hand
    {
        Right,
        Left,
        Either,
    }

    [Tooltip("どちらの手のトリガーで録音するか")]
    [SerializeField] private Hand hand = Hand.Right;
    [Tooltip("スペースキーでも録音できるようにする (エディタ確認用)")]
    [SerializeField] private bool allowKeyboard = true;

    [Header("振動")]
    [SerializeField] private bool haptics = true;
    [SerializeField, Range(0f, 1f)] private float hapticAmplitude = 0.5f;
    [SerializeField] private float hapticSeconds = 0.06f;

    PushToTalkTranscriber transcriber;
    OVRInput.Controller activeController = OVRInput.Controller.None;
    bool keyboardHeld;
    Coroutine hapticRoutine;

    void Awake()
    {
        transcriber = GetComponent<PushToTalkTranscriber>();
    }

    void Update()
    {
        if (activeController == OVRInput.Controller.None && !keyboardHeld)
        {
            // 押し始め
            var pressed = TriggerDown();
            if (pressed != OVRInput.Controller.None)
            {
                if (transcriber.BeginTalk())
                {
                    activeController = pressed;
                    Pulse(pressed, 1f);
                }
            }
            else if (allowKeyboard && SpaceDown())
            {
                keyboardHeld = transcriber.BeginTalk();
            }
        }
        else if (activeController != OVRInput.Controller.None)
        {
            // 押したほうの手のトリガーを離したら送信
            if (!OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, activeController))
            {
                transcriber.EndTalk();
                Pulse(activeController, 0.5f);
                activeController = OVRInput.Controller.None;
            }
        }
        else if (keyboardHeld && !SpaceHeld())
        {
            transcriber.EndTalk();
            keyboardHeld = false;
        }

        // 最大秒数で自動停止した場合などに入力側の状態を戻す
        if (transcriber.State != PushToTalkTranscriber.TalkState.Recording)
        {
            if (activeController != OVRInput.Controller.None && !OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, activeController))
                activeController = OVRInput.Controller.None;
            if (keyboardHeld && !SpaceHeld()) keyboardHeld = false;
        }
    }

    OVRInput.Controller TriggerDown()
    {
        if (hand != Hand.Left && OVRInput.GetDown(OVRInput.Button.PrimaryIndexTrigger, OVRInput.Controller.RTouch))
            return OVRInput.Controller.RTouch;
        if (hand != Hand.Right && OVRInput.GetDown(OVRInput.Button.PrimaryIndexTrigger, OVRInput.Controller.LTouch))
            return OVRInput.Controller.LTouch;
        return OVRInput.Controller.None;
    }

    void Pulse(OVRInput.Controller controller, float strength)
    {
        if (!haptics || controller == OVRInput.Controller.None) return;
        if (hapticRoutine != null) StopCoroutine(hapticRoutine);
        hapticRoutine = StartCoroutine(PulseRoutine(controller, hapticAmplitude * strength));
    }

    IEnumerator PulseRoutine(OVRInput.Controller controller, float amplitude)
    {
        OVRInput.SetControllerVibration(1f, amplitude, controller);
        yield return new WaitForSecondsRealtime(hapticSeconds);
        OVRInput.SetControllerVibration(0f, 0f, controller);
        hapticRoutine = null;
    }

    void OnDisable()
    {
        OVRInput.SetControllerVibration(0f, 0f, OVRInput.Controller.Touch);
        if (activeController != OVRInput.Controller.None || keyboardHeld) transcriber.CancelTalk();
        activeController = OVRInput.Controller.None;
        keyboardHeld = false;
    }

    static bool SpaceDown()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.spaceKey.wasPressedThisFrame;
#else
        return Input.GetKeyDown(KeyCode.Space);
#endif
    }

    static bool SpaceHeld()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.spaceKey.isPressed;
#else
        return Input.GetKey(KeyCode.Space);
#endif
    }
}
