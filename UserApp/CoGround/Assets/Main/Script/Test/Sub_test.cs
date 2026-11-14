using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using StringMsg = RosMessageTypes.Std.StringMsg;

public class Sub_test : MonoBehaviour{

    void Start(){
        ROSConnection.instance.Subscribe<StringMsg>("test1", Callback);
    }

    void Callback(StringMsg msg){
        Debug.Log(msg.data);
    }

}
