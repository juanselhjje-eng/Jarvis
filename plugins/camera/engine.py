from __future__ import annotations
import time
from pathlib import Path

class CameraEngine:
    def __init__(self):
        self.cap=None
        self.available=False
    def start(self,index=0):
        try:
            import cv2
            self.cap=cv2.VideoCapture(int(index))
            self.available=bool(self.cap and self.cap.isOpened())
            return self.available
        except Exception:
            self.cap=None; self.available=False; return False
    def read(self):
        if not self.cap: return None
        ok,frame=self.cap.read()
        return frame if ok else None
    def snapshot(self,destination):
        frame=self.read()
        if frame is None: return None
        import cv2
        p=Path(destination); p.parent.mkdir(parents=True,exist_ok=True)
        cv2.imwrite(str(p),frame)
        return p
    def stop(self):
        if self.cap:
            try:self.cap.release()
            except Exception:pass
        self.cap=None; self.available=False
