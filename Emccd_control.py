import pylablib as pll
from pylablib.devices import Andor
import numpy as np
import matplotlib.pyplot as plt

import time
from PyQt5.QtCore import QObject, QThread, pyqtSignal ,QTimer


# atmcd64d.dll or atmcd64d_legacy.dll
pll.par["device/dlls/andor_sdk2"] = "path/to/SDK2/dlls"
# pll.par['devices/dlls/andor_sdk2']='path/to/dll/'
# Andor.get_cameras_number_SDK2()
# Andor.get_device_info()

class TemperatureControl(QThread):
    
    # 온도 업데이트 시그널
    temperature_update_signal = pyqtSignal(float)

    def __init__(self, cam, temperature):
        super(TemperatureControl, self).__init__()
        self.cam = cam
        self.old_set_temperature = None
        self.new_set_temperature = temperature
        self.running = True

    def set_target_temperature(self, temperature):
        self.new_set_temperature = temperature

    # 현재온도와 설정된 온도가 다르면 설정된 온도로 변경    
    def run(self):
        while self.running:
            if self.old_set_temperature != self.new_set_temperature:
                self.old_set_temperature = self.new_set_temperature
                self.cam.set_temperature(self.new_set_temperature)  

            current_temperature = self.cam.get_temperature() 
            self.temperature_update_signal.emit(current_temperature)
            time.sleep(10)

    def stop(self):
        self.running = False



class EmccdContorl(QThread):
    
    graph_update_signal = pyqtSignal(np.ndarray)
    log_signal = pyqtSignal(str)
    
    def __init__(self,cam,temperature,binning,exposer_time,gain,count):
        
        super(EmccdContorl,self).__init__()
        
        # EMCCD 설정에 관련된 인스턴스 변수들
        
        self.cam = cam
        self.temperature = temperature
        self.binning = binning 
        self.exposer_time = exposer_time
        self.gain = gain
        self.init_count = 0
        self.count = count
        
        # 내장함수 cam_connect로 class를 불러오면 바로 카메라를 연결하도록
        self.cam = self.cam_connect() 

        # EMCCD로 촬영 후 이미지를 저장할 때 필요한 인스턴스 변수들
        self.is_quantum_image = False
        self.save_imgae = False
        self.file_path = None
        self.data_combined_array = None

        # 코드가 실행중이면 True!
        self.is_running = True

    # EMCCD를 연결하고 EMCCD 기본 세팅하는 부분

    def cam_connect(self):
        # 카메라 인스턴스 생성
        cam1 = Andor.AndorSDK2Camera(idx=0)
        # 카메라 연결
        cam1.open()

        # 쿨러 시작 및 온도 설정
        cam1.set_fan_mode("full")
        cam1_info = cam1.get_device_info()
        # self.add_log_message(f"CAM INFO : {cam1_info} 연결")
        cam1_shutter=cam1.setup_shutter("open")
        
        # self.button_unlock()
        
        return cam1  

    def cam_close(self):
        self.cam.close()
    
    def stop(self):
        self.is_running = False
        
    def save_image_function(self , file_path):
        self.file_path = file_path
        self.save_imgae = True

    def setting_emccd(self):
        
        self.cam.set_EMCCD_gain(gain = self.gain)
        self.cam.get_temperature_range() 
        self.cam.set_temperature(temperature = self.temperature, enable_cooler= True) # unit = [C]
        
        self.cam.set_cooler(on = True)

        self.cam.set_fan_mode("full") 

        cam_temperature = self.cam.get_temperature()
        print(f"{cam_temperature}")
        
        # 설정 온도 확인하기
        while cam_temperature > temperature:
            print("온도 설정중")
            time.sleep(10)
            
            cam_temperature = self.cam.get_temperature()
            print(f"CAM TEMPERATURE : {cam_temperature}")

        print("설정 온도도달")
        

    # 측정(aquisition)하기 이전 세팅과 측정에 관련된 함수들
        
    def setting_emccd_aquisition(self):

        self.cam.set_exposure(exposure = self.exposer_time)
        self.cam.set_read_mode(mode="image") # FVB, Image,...
        self.cam.setup_image_mode(hbin=self.binning, vbin=self.binning)
        self.cam.set_EMCCD_gain(self.gain)

        self.cam.set_acquisition_mode(mode = "cont")
        self.cam.setup_acquisition()
        
        print(f"{self.cam.get_acquisition_progress()}")
    
    # 측정(aquisition)하기

    def run(self):
        
        self.cam.set_exposure(exposure = self.exposer_time)
        self.cam.set_read_mode(mode="image") # FVB, Image,...
        self.cam.setup_image_mode(hbin=self.binning, vbin=self.binning)
        self.cam.set_EMCCD_gain(self.gain)

        self.cam.set_acquisition_mode(mode = "cont")
        self.cam.setup_acquisition()
        
        # Return either ``"idle"`` (no acquisition), ``"acquiring"`` (acquisition in progress) or ``"temp_cycle"`` (temperature cycle in progress).
        # 카메라가 아무일도 안하고 대기 상태니...? # idler가 아니라 idle이다...
        
        if self.cam.get_status() == "idle":

            # 측정 시작
            self.cam.start_acquisition()
            self.log_signal.emit("Acquisitioning...")
            self.init_count = 0
            
            while self.cam.acquisition_in_progress():
                if not self.is_running:
                    self.cam.stop_acquisition()
                    self.log_signal.emit("Acquisition stop")
                    break
               
                
                self.init_count += 1
                self.cam.wait_for_frame()

                # 이미지 프레임 얻기
                frame = self.cam.read_oldest_image()
               
                frame = frame[::-1, ::-1]
                # 그래프 업데이트 신호 발생
                self.graph_update_signal.emit(frame)


                # 원하는 프레임 갯수 획득시 종료
                if self.save_imgae:
                    if self.data_combined_array is None:
                        self.init_count = 0
                        self.data_combined_array = np.empty((frame.shape[0], frame.shape[1], self.count))

                    self.data_combined_array[:, :, self.init_count] = frame

                    self.log_signal.emit(f"{self.init_count+1} /{self.count}")

                    if self.init_count+1 >= self.count:
                        self.save_imgae = False
                        self.save_frame(self.data_combined_array)
                        self.data_combined_array = None
                        file_name = self.file_path.split("/")[-1]
                        self.log_signal.emit(f"Save Complete : {file_name}")



    def stop_acquisition(self):
        self.cam.stop_acquisition()
        self.is_running = False

    def save_frame(self, data):
        # frame 저장하기
        np.save(self.file_path, data)

        
if __name__ == "__main__":
    
    temperature = 20
    binning = 3
    exposer_time = 0.1
    gain = 1
    count = 10
    file_path = "D:\\Python_Code\\EMCCD_Result\\data.npy"

    emccd = EmccdContorl(temperature,binning,exposer_time,gain,count)
    
    emccd.setting_emccd()
    # emccd.setting_emccd_aquisition()
    emccd.run()
    emccd.stop_acquisition()
    
    