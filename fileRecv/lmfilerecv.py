#-*- coding: utf-8 -*-
# lmfilerecv.py (Web Server only)
# lmagent로부터 파일과 메타데이터를 수신하여 지정된 경로에 저장하는 역할만 수행.

import os
import sys
import json
import traceback
from flask import Flask, request, jsonify

# --- 전역 설정 변수 ---
CONFIG = {}

# --- 웹 서버 (파일 수신) ---
app = Flask(__name__)

@app.route('/opcFileSave', methods=['POST'])
def file_receiver():
    """
    lmagent로부터 파일 및 파라미터를 수신하여 저장.
    """
    try:
        # 폼 데이터에서 파라미터 추출
        params = {key: request.form[key] for key in request.form}
        deviceid = params.get('deviceid')
        dataid = params.get('dataid')
        org_filename = params.get('orgfilename')

        if not deviceid or not dataid or not org_filename:
            return jsonify({"success": False, "error": "deviceid, dataid 또는 orgfilename이 누락됨"}), 400

        # 파일 저장 경로 설정
        save_path = CONFIG.get('save_path')
        if not save_path:
            return jsonify({"success": False, "error": "서버에 save_path가 설정되지 않음"}), 500
            
        target_dir = os.path.join(save_path, deviceid, dataid)
        os.makedirs(target_dir, exist_ok=True) # 폴더가 없으면 생성
        
        filepath = os.path.join(target_dir, org_filename)
        param_filepath = filepath + '.json'

        # 파일 저장
        file = request.files.get('filename')
        if file:
            # 파일 저장 시 충돌을 피하기 위해 임시 파일명 사용 후 rename
            temp_filepath = filepath + ".tmp"
            file.save(temp_filepath)
            os.rename(temp_filepath, filepath)
            print(f"[INFO] 파일 수신 및 저장 완료: {filepath}")
        else:
            return jsonify({"success": False, "error": "파일 데이터가 없음"}), 400

        # 파라미터 .json 파일로 저장
        with open(param_filepath, 'w', encoding='utf-8') as f:
            json.dump(params, f, indent=2)
        
        return jsonify({"success": True, "message": f"{org_filename} 저장 완료"})

    except Exception as e:
        print(f"[ERROR] 파일 수신 중 오류 발생: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# --- 메인 실행 블록 ---
if __name__ == '__main__':
    # 1. 설정 파일 로드
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            CONFIG = json.load(f)
    except FileNotFoundError:
        print("[CRITICAL] 서버 설정 파일(config.json)을 찾을 수 없습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    except Exception as e:
        print(f"[CRITICAL] 서버 설정 파일(config.json) 읽기 오류: {e}. 프로그램을 종료합니다.")
        sys.exit(1)

    # 2. 저장 경로 확인 및 생성
    save_path = CONFIG.get('save_path')
    if save_path:
        os.makedirs(save_path, exist_ok=True)
        print(f"[INFO] 저장 경로 확인/생성: {save_path}")
    else:
        print("[CRITICAL] config.json에 'save_path'가 정의되지 않았습니다. 프로그램을 종료합니다.")
        sys.exit(1)

    # 3. Flask 웹 서버 시작
    print("[INFO] Flask 웹 서버를 0.0.0.0:8080에서 시작합니다.")
    app.run(host='0.0.0.0', port=8080)