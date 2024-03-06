import sys,os
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import QThread, pyqtSignal ,QTimer
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from Emccd_control_final import EmccdContorl, TemperatureControl # EmccdControl, TemperatureControl class import

import pylablib as pll
from pylablib.devices import Andor
pll.par["devices/dlls/andor_sdk2"] = "path/to/dlls"


class EmccdGui(QMainWindow):
    
    def __init__(self) -> None:
        super().__init__()
    
        # Emccd camera parameter
        self.temperature = -60
        self.binning = 3
        self.exposure_time = 1
        self.gain = 3
        self.count =  1
        
        self.rectangle_width = 30
        self.rectangle_hight = 30
        self.rectangle_distance = 90
        
        self.colorbar = None
        
        # read of image => 직사각형 사이즈를 조절하는 파라미터를 사용할지 고민
        
        # GUI function
        self.initUI()
        
        # camera connect and thread
        self.cam = self.emccd_connect()
        self.cam_thread = EmccdContorl(self.cam,self.temperature,self.binning,self.exposure_time,self.gain,self.count)
        
        # temperature control thread
        self.temperature_thread = TemperatureControl(self.cam, self.temperature)
        self.temperature_thread.temperature_update_signal.connect(self.temperature_display)
        self.temperature_thread.start()
        self.temperature_thread.temperature_update_signal.connect(self.temperature_display)
    
    def emccd_connect(self):
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
    
    # GUI layout    
    def initUI(self):
        
        # total layout
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)
        
        # 창 크기 기본설정 확인 필요
        # self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('Emccd Acquisition Control')
        
        # Main layout에 모두 추가하기
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)
        
        # Left => Emccd graph display
        self.figure, self.ax = plt.subplots()
        self.ax.set_aspect('equal')
        # set_title = self.ax.set_title('Emccd Image')
        self.canvas = FigureCanvas(self.figure)
        
        self.main_layout.addWidget(self.canvas,1)
    
    
        # Right => Emccd acquisition
        # widget으로 한 번더 감싸줘야한다!!!
        # main widget => main layout => ★★★control widget★★★ => right layout => right layout_1, right layout_2, right layout_3, right layout_4, right layout_5
        self.control_widget = QWidget()
        self.right_layout = QVBoxLayout(self.control_widget)
        self.main_layout.addWidget(self.control_widget,0)
        
        
        # 1. 메모장 
        # 현재 저장한 row data나 graph를 보여주는 창으로 사용할 계획
        # 그럴려면 저장했을 때 정보를 나타내는 함수와 그 함수에 로그를 내보내는 기능이 필요
        
        self.right_layout_1 = QVBoxLayout()
        self.right_layout.addLayout(self.right_layout_1)
        self.right_layout_1.addStretch(1) 
        
        self.label_1 = QLabel("현재 측정한 데이터,이미지")
        self.right_layout_1.addWidget(self.label_1)
        
        self.tem_status = QLineEdit()
        self.right_layout_1.addWidget(self.tem_status)
        
    
        # 2. Emccd parameter control 창   
        
        self.right_layout_2 = QHBoxLayout()
        self.right_layout.addLayout(self.right_layout_2)
        
        # 2-1. temperature , binning, exposer time, gain, count 설정창
        
        self.right_layout_2_1 = QVBoxLayout()
        self.right_layout_2.addLayout(self.right_layout_2_1)
        
        self.label_temperature = QLabel("temperature")        
        self.right_layout_2_1.addWidget(self.label_temperature)
              
        self.label_binning = QLabel("binning")        
        self.right_layout_2_1.addWidget(self.label_binning)
        
        self.label_exposer_time = QLabel("exposer time")       
        self.right_layout_2_1.addWidget(self.label_exposer_time)
        
        self.label_gain = QLabel("gain")        
        self.right_layout_2_1.addWidget(self.label_gain)
        
        self.label_count = QLabel("count")        
        self.right_layout_2_1.addWidget(self.label_count)
                
        
        # 2-2. temperature , binning, exposer time, gain, count QlineEdit창
        
        self.right_layout_2_2 = QVBoxLayout()
        self.right_layout_2.addLayout(self.right_layout_2_2)
        
        self.temperature_input = QLineEdit()
        self.right_layout_2_2.addWidget(self.temperature_input)
        
        self.binning_input = QLineEdit()
        self.right_layout_2_2.addWidget(self.binning_input)
        
        self.exposure_time_input = QLineEdit()
        self.right_layout_2_2.addWidget(self.exposure_time_input)
        
        self.gain_input = QLineEdit()
        self.right_layout_2_2.addWidget(self.gain_input)
        
        self.count_input = QLineEdit()
        self.right_layout_2_2.addWidget(self.count_input)
    
        
        # temperature , binning, exposer time, gain, count 초기값 설정
        
        self.temperature_input.setText(f"{self.temperature}")
        self.binning_input.setText(f"{self.binning}")
        self.exposure_time_input.setText(f"{self.exposure_time}")
        self.gain_input.setText(f"{self.gain}")
        self.count_input.setText(f"{self.count}")
        
        # 3. Acquistion button
        
        self.right_layout_3 = QVBoxLayout()
        self.right_layout.addLayout(self.right_layout_3) 
        
        self.btn_acquisiton = QPushButton('Acquistion')
        self.right_layout_3.addWidget(self.btn_acquisiton)
        
        # 4. Stop button
        
        self.right_layout_4 = QVBoxLayout()
        self.right_layout.addLayout(self.right_layout_4)
        
        self.btn_stop = QPushButton('Stop')
        self.right_layout_4.addWidget(self.btn_stop)
        
        # 5. Save button
        
        self.right_layout_5 = QHBoxLayout()
        self.right_layout.addLayout(self.right_layout_5) 
        
        self.btn_data_save = QPushButton('Data save')
        self.right_layout_5.addWidget(self.btn_data_save)
        
        self.btn_fig_save = QPushButton('Fig save')
        self.right_layout_5.addWidget(self.btn_fig_save)
        
        self.btn_close = QPushButton('close')
        self.right_layout_5.addWidget(self.btn_close)
        
        # button 기능(함수) 연결
        
        self.btn_acquisiton.clicked.connect(self.Acquistion_event)
        self.btn_stop.clicked.connect(self.Stop_event) 
        self.btn_data_save.clicked.connect(self.Data_save_event) 
        self.btn_fig_save.clicked.connect(self.Fig_save_event)
        self.btn_close.clicked.connect(self.Close_event)
    
        # 입력창 변경시 변수에 저장 
        
        self.temperature_input.textChanged.connect(self.temperature_input_change)
        self.binning_input.textChanged.connect(self.binning_input_change)
        self.exposure_time_input.textChanged.connect(self.exposure_time_input_change)
        self.gain_input.textChanged.connect(self.gain_input_change)
        self.count_input.textChanged.connect(self.count_input_change)
        
        # setplaceholderText => 입력창에 힌트를 넣어줌
        
        self.temperature_input.setPlaceholderText("온도 입력")
        self.binning_input.setPlaceholderText("한번에 같이 볼 pixel 수 입력")
        self.exposure_time_input.setPlaceholderText("노출시간 입력")
        self.gain_input.setPlaceholderText("감도 입력")
        self.count_input.setPlaceholderText("이미지 개수 입력")
        
        # grid box checkbox
        self.right_layout_6 = QVBoxLayout()
        self.right_layout.addLayout(self.right_layout_6)
        
        self.grid_label = QLabel("Grid")
        self.right_layout_6.addWidget(self.grid_label)
        
        self.checkbox_grid = QCheckBox("Grid")
        self.checkbox_grid.stateChanged.connect(self.grid_event)
        self.right_layout_6.addWidget(self.checkbox_grid)
        
        self.grid_size_label = QLabel("Grid Size")
        self.right_layout_6.addWidget(self.grid_size_label)
        
        # grid size input
        if self.checkbox_grid.isChecked():
            self.grid_size_input = QLineEdit(f"{self.binning} * {self.rectangle_width} * 13 " + " um")
        else:
            self.grid_size_input = QLineEdit("gird checkbox not checked")
            
        
        # 입력칸 라벨링
        self.log_label = QLabel("Log", self.control_widget)
        self.right_layout.addWidget(self.log_label)


        # log 카메라 온도 표시
        self.log_text_edit = QTextEdit(self.control_widget)
        self.log_text_edit.setReadOnly(True)
        self.right_layout.addWidget(self.log_text_edit,1)
        self.current_temperature_label = QLabel("Current Temperature: --°C", self.control_widget)
        self.right_layout.addWidget(self.current_temperature_label)
        
        # 입력 지연 설정
        self.input_delay_timer = QTimer(self)
        self.input_delay_timer.setSingleShot(True)


    def grid_event(self, frame):
        # 체크박스 체크 되었을경우 그리드 표시
        center = (frame.shape[0]) / 2

        # Signal 영역 설정
        self.x_in_dx ,self.x_fin_dx = round(center - self.rectangle_width / 2), round(center + self.rectangle_width / 2)
        self.y_in_dx ,self.y_fin_dx = round(center - self.rectangle_hight / 2 -self.rectangle_distance), round(center + self.rectangle_hight / 2 -self.rectangle_distance) 

        # idler 영역 설정
        self.x_in_sx ,self.x_fin_sx = round(center - self.rectangle_width / 2), round( center + self.rectangle_width / 2)
        self.y_in_sx ,self.y_fin_sx = round( center - self.rectangle_hight / 2 + self.rectangle_distance),round( center + self.rectangle_hight / 2 + self.rectangle_distance)

        
        if self.checkbox_grid.isChecked():
            # Signal 영역 표시
            idler_rect  = Rectangle((self.x_in_dx, self.y_in_dx), self.x_fin_dx - self.x_in_dx, self.y_fin_dx - self.y_in_dx, fill=False, edgecolor='blue', linestyle='--',label='Signal Area (Upper)')
            self.ax.add_patch(idler_rect)
            # # Idler 영역 표시 (상하 대칭)
            signal_rect = Rectangle((self.x_in_sx, self.y_in_sx), self.x_fin_sx - self.x_in_sx, self.y_fin_sx - self.y_in_sx, fill=False, edgecolor='red', linestyle='--', label='Idler Area (Lower)')
            self.ax.add_patch(signal_rect)

            # 그래프 중앙선
            self.ax.axvline(center, color='gray', linestyle='--')  
            self.ax.axhline(center, color='gray', linestyle='--')  
        
        self.canvas.draw()
    
    
    def add_log_message(self, message):
        self.log_text_edit.append(message)
    
    def temperature_display(self, temperature):
        self.current_temperature_label.setText(f"Current Temperature: {temperature:.2f}°C")
        pass        
    
        
    def Acquistion_event(self):
        # 측정 시작시 버튼 비활성화
        self.button_lock()
        
        if hasattr(self, 'cam_thread') and self.cam_thread.isRunning():
            self.cam_thread.terminate()

        self.cam_thread = EmccdContorl(self.cam, self.count, self.temperature, self.exposure_time, self.binning, self.gain)
        self.cam_thread.graph_update_signal.connect(self.update_graph)
        self.add_log_message("측정을 시작합니다")
        self.cam_thread.start()
        self.cam_thread.graph_update_signal.connect(self.update_graph)
        
        # 측정 종료시 기능 활성화
        self.cam_thread.finished.connect(self.button_unlock)
    

    def Stop_event(self):
        self.cam_thread.stop()
        # self.temperature_thread.stop()
        self.add_log_message("측정을 종료합니다")
        self.button_unlock()
    
    
    # 측정 시작하면 버튼 비활성화 하는
    def button_lock(self):
        
        self.btn_acquisiton.setEnabled(False)
        self.count_input.setEnabled(False)
        self.temperature_input.setEnabled(False)
        self.exposure_time_input.setEnabled(False)
        self.binning_input.setEnabled(False)
        self.gain_input.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_data_save.setEnabled(True)
        self.btn_fig_save.setEnabled(True)
        self.btn_close.setEnabled(False)


    # 측정 종료하면 버튼 활성화 
    def button_unlock(self):
        
        self.btn_acquisiton.setEnabled(True)
        self.count_input.setEnabled(True)
        self.temperature_input.setEnabled(True)
        self.exposure_time_input.setEnabled(True)
        self.binning_input.setEnabled(True)
        self.gain_input.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_data_save.setEnabled(True)
        self.btn_fig_save.setEnabled(True)
        self.btn_close.setEnabled(True)
    
    
    
    # emccd graph display 부분에 그래프 업데이프 하는 함수
    def update_graph(self, frame):
        
        # self.add_log_message("updating graph...")
        
        self.ax.clear()
        
        # frame[frame<0] = 0  
        im = self.ax.imshow(frame , cmap='viridis')
        
        if not self.colorbar:
            self.colorbar = plt.colorbar(im, ax=self.ax)
        else:
            self.colorbar.update_normal(im)
        
        self.ax.set_title('Emccd Image')
        self.canvas.draw()

    
    # 데이터(raw data) 저장
    def Data_save_event(self):
        options = QFileDialog.Options()
        file_name_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", ";;All Files (*);;NPY Files (*.npy)", options=options)
        if file_name_path:
            self.cam_thread.save_image_function(file_name_path)
            self.add_log_message(f"Data save : {file_name_path}")

    
    # 그래프(graph) 그림 저장
    def Fig_save_event(self):
        options = QFileDialog.Options()
        file_name_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*);;PNG Files (*.png);;JPEG Files (*.jpg)", options=options)
        if file_name_path:
            self.figure.savefig(file_name_path)
            file_name = file_name_path.split("/")[-1]
            self.add_log_message(f"Figure save : {file_name}")
            
    
    # 위젯이 종료될 때 실행되는 함수
    def Close_event(self,event):
        
        reply = QMessageBox.question(self, 'Message', 'Are you sure you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.cam.stop_acquisition()
            self.temperature_thread.stop()
            self.cam.stop_acquisition()
            self.cam.setup_shutter("closed")
            self.cam.close()
            print("cam 연결 종료")
            event.accept()  # 위젯 닫기 이벤트 수락
        else:
            event.ignore()  # 위젯 닫기 이벤트 무시


    # EMCCD 변수 입력창 값 변경시 해당변수에 변경 값 저장

    def count_input_change(self, text):
        self.input_delay_timer.start(1000)
        try:
            self.count = int(text)
        except:
            self.count = 1

    def temperature_input_change(self, text):
        self.input_delay_timer.start(1000)
        try:
            self.temperature = float(text)
        except:
            self.temperature = -60

        self.temperature_thread.set_target_temperature(self.temperature)
        
    def exposure_time_input_change(self, text):
        self.input_delay_timer.start(1000)
        try:
            self.exposure_time = float(text)
        except:
            self.exposure_time = 1

    def binning_input_change(self, text):
        self.input_delay_timer.start(1000)
        try:
            self.binning = int(text)
        except:
            self.binning = 3
            
    def gain_input_change(self, text):
        self.input_delay_timer.start(1000)
        try:
            if int(text) > 300:
                self.gain = 3
            self.gain = int(text)
        except:
            self.gain = 3


# 이 코드에서 실행시, 앱 실행하는 코드

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    camgui = EmccdGui()
    camgui.show()
    
    sys.exit(app.exec_())