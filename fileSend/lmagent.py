#-*- coding: utf-8 -*-
# lmagent.py
# 이 스크립트는 설정 파일(config.json)에 지정된 경로를 주기적으로 스캔함.
# 마지막으로 확인한 시간(lastchktime) 이후에 수정된 파일을 찾아내어,
# 지정된 게이트웨이(gateway_url)로 HTTP POST를 통해 전송하는 에이전트 역할을 함.

import sys
import time
import datetime
import json
import socket
import os
import requests
import logging
import re

def timefmt(t):
    # time.time() 등으로 얻어온 타임스탬프 값을 'Y-m-d H:M:S' 형태의 문자열로 변환하는 함수이다.
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))

def getValue(obj, key, defval):
    # 설정(config) 객체에서 키(key)에 해당하는 값을 찾아 반환함.
    # 만약 키가 존재하지 않으면 기본값(defval)을 반환한다.
    # 값에 "$HOSTNAME"이라는 문자열이 있으면, 현재 장비의 호스트 이름으로 교체한다.
    if key in obj:
        v = obj[key]
        if type(v) == str:
            v = v.replace("$HOSTNAME", socket.gethostname())
        return v
    else:
        return defval

def get_files_to_send(paths_str, dataids_str, headerlines_str, fexts_str, last_check_time):
    # 전송해야 할 파일 목록을 찾아내는 함수이다.
    # 마지막 확인 시간(last_check_time) 이후에 수정된 파일만 대상으로 한다.
    
    files_to_send = []  # 전송 대상 파일 정보를 담을 리스트.
    
    # 설정 파일에 콤마(,)로 구분된 여러 경로가 있을 수 있으므로 분리해서 처리.
    paths = paths_str.split(",")
    dataids = dataids_str.split(",")
    fexts = fexts_str.split(",")
    # headerline 문자열을 파싱하여 리스트로 변환 (예: "1,1,[1,2],1" -> ['1', '1', '[1,2]', '1'])
    headerlines = re.findall(r'(\[[^\]]+\]|[^,]+)', headerlines_str)

    # 각 경로를 순회하며 파일을 스캔한다.
    for index, directory in enumerate(paths):
        try:
            # 해당 디렉토리의 파일 목록을 가져온다.
            files = os.listdir(directory)
        except Exception as e:
            logging.error(f"디렉토리({directory}) 확인 중 오류 발생: {e}")
            continue  # 접근할 수 없는 디렉토리는 건너뛴다.

        dataid = dataids[index]
        headerline = headerlines[index] # 현재 경로에 맞는 headerline을 가져옴
        # 디렉토리 내의 각 파일에 대해 처리.
        for file in files:
            # 파일 이름과 확장자를 소문자로 분리.
            fname, fext = os.path.splitext(file.lower())
            
            # 엑셀 등에서 작업 시 생성되는 임시 파일(~$로 시작)은 건너뛴다.
            if fname.startswith("~$"):
                continue

            file_path = os.path.join(directory, file)
            # 해당 경로가 디렉토리가 아니고, 스캔 대상 확장자(fexts)에 포함되는지 확인.
            if (not os.path.isdir(file_path)) and (fext in fexts):
                try:
                    # 파일의 최종 수정 시간을 타임스탬프로 가져온다.
                    mtime = os.path.getmtime(file_path)
                    # 파일의 수정 시간이 마지막 확인 시간보다 최신인 경우.
                    if mtime > last_check_time:
                        # 전송 목록에 파일 정보(경로, 데이터 ID, 헤더라인, 수정 시간)를 추가.
                        files_to_send.append({
                            'file_path': file_path,
                            'dataid': dataid,
                            'headerline': headerline,
                            'mtime': mtime
                        })
                except FileNotFoundError:
                    # 스캔 도중 파일이 삭제되는 경우를 대비한 예외 처리.
                    logging.warning(f"스캔 중 파일을 찾을 수 없음: {file_path}")
                    continue
    
    # 전송할 파일들을 수정 시간(mtime) 기준으로 오름차순 정렬. (오래된 파일부터 보내기 위함)
    files_to_send.sort(key=lambda x: x['mtime'])
    return files_to_send

def update_lastchktime_in_config(new_time_str):
    # config.json 파일의 lastchktime 값을 안전하게 업데이트하는 함수이다.
    try:
        # 설정 파일을 읽어서 JSON 객체로 로드.
        with open("config.json", "r") as f:
            config = json.load(f)
        
        # lastchktime 값을 새로운 시간 문자열로 변경.
        config['lastchktime'] = new_time_str
        
        # 수정된 config 객체를 다시 파일에 덮어쓴다. (indent=2로 가독성 좋게 저장)
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        logging.info(f"lastchktime 값을 다음으로 업데이트: {new_time_str}")
    except Exception as e:
        logging.error(f"config.json 업데이트 중 오류 발생: {e}")


if __name__ == '__main__':
    # --- 로깅 설정 ---
    logging.basicConfig(
        level=logging.INFO,  # INFO 레벨 이상의 로그만 기록함.
        format='%(asctime)s - %(levelname)s - %(message)s',  # 로그 형식: 시간 - 레벨 - 메시지
        filename='agent.log',  # 로그를 기록할 파일 이름.
        filemode='a'  # 'a'는 이어쓰기 모드(기존 로그에 추가), 'w'는 덮어쓰기 모드.
    )
    # 콘솔(화면)에도 로그를 함께 출력하기 위해 핸들러 추가.
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    logging.info("===== LM Agent 시작 =====")

    # 스크립트의 메인 실행 부분.
    # 무한 루프를 돌면서 주기적으로 파일 스캔 및 전송을 수행한다.
    while True:
        config = None
        # --- 1. 설정 파일 로드 ---
        try:
            with open("config.json", "r") as json_file:
                config = json.load(json_file)
        except Exception as e:
            logging.exception("config.json 로드 오류. 10초 후 재시도...")
            time.sleep(10) # 설정 파일이 없거나 깨졌을 경우 10초 후 다시 시도.
            continue

        # --- 2. 설정 값 파싱 ---
        gateway_url = getValue(config, 'gateway_url', "")
        scan_path_str = getValue(config, 'scan_path', "")
        scan_file_str = getValue(config, 'scan_file', ".csv,.xls,.xlsx,.dbf").lower()
        deviceid = getValue(config, 'deviceid', "")
        dataid_str = getValue(config, 'dataid', "")
        scan_interval = getValue(config, 'scan_interval', 60)
        lastchktime_str = getValue(config, 'lastchktime', "1970-01-01 00:00:00")
        headerline_str = getValue(config, 'headerline', '1') 

        # 마지막 확인 시간을 문자열에서 타임스탬프(float)로 변환.
        lastmtime_ts = time.mktime(datetime.datetime.strptime(lastchktime_str, '%Y-%m-%d %H:%M:%S').timetuple())
        
        logging.info(f"설정된 시간({lastchktime_str}) 이후로 수정된 파일을 스캔합니다...")
        
        # --- 3. 전송 대상 파일 목록 가져오기 ---
        slist = get_files_to_send(scan_path_str, dataid_str, headerline_str, scan_file_str, lastmtime_ts)

        # --- 4. 파일 전송 처리 ---
        if not slist:
            # 전송할 파일이 없는 경우.
            logging.info("새로 전송할 파일이 없습니다.")
            # 파일이 없더라도 게이트웨이 서버에 살아있다는 신호(live check)를 보낼 수 있음 (선택 사항).
            try:
                params = {'deviceid': deviceid, 'dataid': "-", 'path': "-", 'orgfilename': '-', 'headerline': '-', 'params': "deviceid,dataid,path,orgfilename,headerline"}
                upload = {'filename': ""}
                requests.post(url=gateway_url, timeout=10, data=params, files=upload)
            except Exception as e:
                logging.warning(f"Live-check 전송 오류: {e}")
        else:
            # 전송할 파일이 있는 경우.
            logging.info(f"총 {len(slist)}개의 새로운 파일을 발견했습니다.")
            # 정렬된 목록(slist)을 순회하며 파일 전송.
            for f_info in slist:
                file_path = f_info['file_path']
                current_dataid = f_info['dataid']
                current_headerline = f_info['headerline']
                file_mtime = f_info['mtime']
                
                path_parts = os.path.split(file_path)
                fname = path_parts[1]
                
                logging.info(f"파일 전송 시도: {fname} (수정 시간: {timefmt(file_mtime)})")

                try:
                    # 파일을 바이너리 읽기 모드('rb')로 연다.
                    with open(file_path, 'rb') as sendfile:
                        # requests로 보낼 파일과 파라미터를 준비.
                        upload = {'filename': sendfile}
                        params = {
                            'deviceid': deviceid,
                            'dataid': current_dataid,
                            'path': current_dataid, # 원본 로직에 따라 path를 dataid로 설정.
                            'orgfilename': fname,
                            'headerline': current_headerline, # 매칭된 headerline 파라미터 추가
                            'params': "deviceid,dataid,filename,path,orgfilename,headerline"
                        }

                        # HTTP POST 요청으로 파일 전송.
                        response = requests.post(url=gateway_url, timeout=60, data=params, files=upload)

                        # --- 5. 전송 성공/실패 처리 ---
                        if response.status_code == 200:
                            # 전송 성공 시 (HTTP 상태 코드 200).
                            logging.info(f"성공적으로 전송 완료: {fname}.")
                            
                            # 중요: config.json의 lastchktime을 방금 보낸 파일의 수정 시간으로 업데이트.
                            update_lastchktime_in_config(timefmt(file_mtime))

                        else:
                            # 전송 실패 시.
                            logging.error(f"전송 실패: {fname}. 상태 코드: {response.status_code}. 이번 주기의 추가 전송을 중단합니다.")
                            # 전송에 실패하면 현재 사이클을 중단. 다음 사이클에서 이 파일부터 다시 시도하게 됨.
                            break

                except Exception as e:
                    # requests.post에서 발생할 수 있는 모든 예외(네트워크 오류 등)를 처리.
                    logging.exception(f"파일({fname}) 전송 중 예외 발생. 이번 주기의 추가 전송을 중단합니다.")
                    # 예외 발생 시에도 현재 사이클을 중단.
                    break
        
        # --- 6. 다음 스캔까지 대기 ---
        logging.info(f"{scan_interval}초 후 다음 스캔을 시작합니다...")
        time.sleep(scan_interval)
