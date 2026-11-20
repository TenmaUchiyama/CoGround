import os 
from ultralytics import YOLOWorld

model = YOLOWorld(os.environ["COGROUND_DETECT_MODEL"]) 
print(type(model))

model.set_classes(["toilet", "food"])

# 2) 画像1枚で推論する（ultralytics に入っている見本画像を使う）
img = "/opt/conda/lib/python3.11/site-packages/ultralytics/assets/bus.jpg"
results = model.predict(img, device="cuda:0", conf=0.25, verbose=False)

# 3) 結果を見る（画像1枚なので results[0]）
r = results[0]
print(r.names)   # {0: 'bus', 1: 'person', 2: 'cup'}
for xyxy, score, cls in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
    print(r.names[int(cls)], round(score, 2), [round(v) for v in xyxy])

# 4) 枠を描いた画像を保存する（/app/logs はホストの grounding_server/logs と同じ場所）
r.save("/app/logs/practice_bus.jpg")