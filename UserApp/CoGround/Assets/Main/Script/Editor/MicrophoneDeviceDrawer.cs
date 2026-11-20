using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

/// <summary>[MicrophoneDevice] の付いた string をマイク一覧のドロップダウンで表示する</summary>
[CustomPropertyDrawer(typeof(MicrophoneDeviceAttribute))]
public class MicrophoneDeviceDrawer : PropertyDrawer
{
    const string DefaultLabel = "(既定のマイク)";

    public override void OnGUI(Rect position, SerializedProperty property, GUIContent label)
    {
        if (property.propertyType != SerializedPropertyType.String)
        {
            EditorGUI.PropertyField(position, property, label);
            return;
        }

        string current = property.stringValue;
        var devices = Microphone.devices;

        var options = new List<string> { DefaultLabel };
        options.AddRange(devices);

        int index = 0;
        if (!string.IsNullOrEmpty(current))
        {
            index = options.IndexOf(current);
            if (index < 0)
            {
                // 保存されているマイクが今は繋がっていない
                options.Add(current + " (未接続)");
                index = options.Count - 1;
            }
        }

        // 名前にスラッシュがあるとサブメニュー扱いになるので置き換えて表示
        var display = new GUIContent[options.Count];
        for (int i = 0; i < options.Count; i++)
            display[i] = new GUIContent(options[i].Replace('/', '∕'));

        EditorGUI.BeginProperty(position, label, property);
        EditorGUI.BeginChangeCheck();
        int selected = EditorGUI.Popup(position, label, index, display);
        if (EditorGUI.EndChangeCheck())
        {
            if (selected == 0) property.stringValue = "";
            else if (selected - 1 < devices.Length) property.stringValue = devices[selected - 1];
            // 「未接続」を選び直した場合は値を変えない
        }
        EditorGUI.EndProperty();
    }
}
