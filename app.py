# app.py
from flask import Flask, render_template, request, jsonify, send_file
import os
import threading
import time
from datetime import datetime
import requests
import json
import html 

app = Flask(__name__)

app_status = {
    'running': False,
    'logs': [],
    'sent_count': 0,
    'remaining_count': 0,
    'total_sent': 0,
    'current_batch': 0,
    'total_batches': 0
}


import threading
status_lock = threading.Lock()

def add_log(message):
    """افزودن لاگ جدید"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"{timestamp} - {message}"
    
    with status_lock:
        app_status['logs'].insert(0, log_entry)  
        if len(app_status['logs']) > 100:  
            app_status['logs'] = app_status['logs'][:100]

def escape_xml(text):
    """تبدیل کاراکترهای مخصوص XML"""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))

def send_sms_batch(numbers, username, password, src_address, message, batch_size=250):
    """ارسال دسته‌ای SMS"""
    url = "https://smsapi.asanak.ir/services/CompositeSmsGateway"
    
    successful_numbers = []
    failed_numbers = []
    
    # تقسیم به دسته‌ها
    batches = []
    for i in range(0, len(numbers), batch_size):
        batch = numbers[i:i + batch_size]
        batches.append(batch)
    
    app_status['total_batches'] = len(batches)
    
    for batch_index, batch_numbers in enumerate(batches, 1):
        if not app_status['running']:
            add_log("⏹️ ارسال متوقف شد")
            break
            
        app_status['current_batch'] = batch_index
        batch_size_actual = len(batch_numbers)
        add_log(f"📦 دسته {batch_index}/{len(batches)} ({batch_size_actual} شماره)")
        
        # ساخت XML
        dest_addresses_xml = ""
        for number in batch_numbers:
            dest_addresses_xml += f"<destAddresses>{number}</destAddresses>\n         "
        
        order_ids_xml = ""
        for _ in batch_numbers:
            order_ids_xml += "<orderIds>1</orderIds>\n         "
        
        # Escape کردن متن پیامک برای XML
        escaped_message = escape_xml(message)
        
        payload = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:web="http://webService.compositeSmsGateway.services.sdp.peykasa.com/">
   <soapenv:Header/>
   <soapenv:Body>
      <web:sendSms>
         <userCredential>
            <password>{password}</password>
            <username>{username}</username>
         </userCredential>
         <srcAddresses>{src_address}</srcAddresses>
         {dest_addresses_xml}
         <msgBody>{escaped_message}</msgBody>
         <msgEncoding>8</msgEncoding>
         {order_ids_xml}
         <campaignIds>1</campaignIds>
      </web:sendSms>
   </soapenv:Body>
</soapenv:Envelope>"""
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        
        try:
            response = requests.post(url, data=payload.encode('utf-8'), headers=headers, timeout=30)
            
            if response.status_code == 200:
                if "<status>0</status>" in response.text:
                    successful_numbers.extend(batch_numbers)
                    add_log(f"✅ دسته {batch_index} موفق ({batch_size_actual} شماره)")
                    app_status['sent_count'] += batch_size_actual
                    app_status['total_sent'] += batch_size_actual
                else:
                    failed_numbers.extend(batch_numbers)
                    add_log(f"⚠️ خطا در دسته {batch_index}")
            else:
                failed_numbers.extend(batch_numbers)
                add_log(f"❌ خطای HTTP در دسته {batch_index}: {response.status_code}")
                
        except Exception as e:
            failed_numbers.extend(batch_numbers)
            add_log(f"❌ خطای شبکه در دسته {batch_index}: {str(e)}")
        
        time.sleep(2)  
    
    return successful_numbers, failed_numbers

def send_sms_process(settings):
    """فرآیند اصلی ارسال"""
    add_log("🚀 شروع فرآیند ارسال")
    
    interval = settings.get('interval', 5)
    
    while app_status['running']:
        try:
            # خواندن شماره‌ها از فایل
            if not os.path.exists('dest-numbers.txt'):
                add_log("⚠️ فایل شماره‌ها یافت نشد")
                break
            
            with open('dest-numbers.txt', 'r', encoding='utf-8') as f:
                all_numbers = [line.strip() for line in f if line.strip()]
            
            app_status['remaining_count'] = len(all_numbers)
            
            if not all_numbers:
                add_log("✅ تمام شماره‌ها ارسال شدند")
                break
            
            add_log(f"📖 خواندن {len(all_numbers)} شماره از فایل")
            
            # ارسال
            successful, failed = send_sms_batch(
                all_numbers,
                settings['username'],
                settings['password'],
                settings['src_address'],
                settings['message'],  # اضافه کردن متن پیامک
                settings['batch_size']
            )
            
            # ذخیره شماره‌های موفق
            if successful:
                with open('processed.txt', 'a', encoding='utf-8') as f:
                    for number in successful:
                        f.write(f"{number}\n")
                add_log(f"💾 {len(successful)} شماره به processed.txt اضافه شد")
            
            # ذخیره شماره‌های ناموفق
            with open('dest-numbers.txt', 'w', encoding='utf-8') as f:
                for number in failed:
                    f.write(f"{number}\n")
            
            if failed:
                add_log(f"⚠️ {len(failed)} شماره ناموفق باقی ماند")
                add_log(f"⏳ منتظر {interval} ثانیه...")
                time.sleep(interval)
            else:
                break
                
        except Exception as e:
            add_log(f"❌ خطا: {str(e)}")
            break
    
    app_status['running'] = False
    add_log("🏁 فرآیند ارسال پایان یافت")

# Routes
@app.route('/')
def index():
    """صفحه اصلی"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """دریافت وضعیت فعلی"""
    # خواندن آمار فایل‌ها
    dest_count = 0
    if os.path.exists('dest-numbers.txt'):
        with open('dest-numbers.txt', 'r', encoding='utf-8') as f:
            dest_count = len([line.strip() for line in f if line.strip()])
    
    processed_count = 0
    if os.path.exists('processed.txt'):
        with open('processed.txt', 'r', encoding='utf-8') as f:
            processed_count = len([line.strip() for line in f if line.strip()])
    
    with status_lock:
        return jsonify({
            'running': app_status['running'],
            'logs': app_status['logs'][:20],  # 20 لاگ آخر
            'sent_count': app_status['sent_count'],
            'remaining_count': dest_count,
            'total_sent': app_status['total_sent'],
            'current_batch': app_status['current_batch'],
            'total_batches': app_status['total_batches'],
            'stats': {
                'remaining': dest_count,
                'processed': processed_count,
                'total': dest_count + processed_count
            }
        })

@app.route('/api/start', methods=['POST'])
def start_sending():
    """شروع ارسال"""
    if app_status['running']:
        return jsonify({'success': False, 'message': 'در حال حاضر در حال ارسال است'})
    
    # دریافت تنظیمات از فرم
    settings = request.json
    
    # اعتبارسنجی
    required_fields = ['username', 'password', 'src_address', 'interval', 'batch_size', 'message']
    for field in required_fields:
        if field not in settings:
            return jsonify({'success': False, 'message': f'فیلد {field} الزامی است'})
    
    # ذخیره شماره‌های وارد شده
    numbers = settings.get('numbers', '')
    if numbers:
        numbers_list = [n.strip() for n in numbers.split('\n') if n.strip()]
        with open('dest-numbers.txt', 'w', encoding='utf-8') as f:
            for num in numbers_list:
                f.write(f"{num}\n")
        add_log(f"✅ {len(numbers_list)} شماره ذخیره شد")
    
    # ذخیره متن پیامک در فایل (اختیاری)
    with open('last_message.txt', 'w', encoding='utf-8') as f:
        f.write(settings['message'])
    
    # شروع فرآیند در thread جداگانه
    app_status['running'] = True
    app_status['sent_count'] = 0
    app_status['current_batch'] = 0
    app_status['total_batches'] = 0
    
    thread = threading.Thread(
        target=send_sms_process,
        args=(settings,),
        daemon=True
    )
    thread.start()
    
    return jsonify({'success': True, 'message': 'ارسال شروع شد'})

@app.route('/api/stop', methods=['POST'])
def stop_sending():
    """توقف ارسال"""
    app_status['running'] = False
    return jsonify({'success': True, 'message': 'درخواست توقف ثبت شد'})

@app.route('/api/numbers', methods=['GET'])
def get_numbers():
    """دریافت شماره‌های موجود"""
    numbers = []
    if os.path.exists('dest-numbers.txt'):
        with open('dest-numbers.txt', 'r', encoding='utf-8') as f:
            numbers = [line.strip() for line in f if line.strip()]
    
    return jsonify({'numbers': '\n'.join(numbers[:100])})  # حداکثر 100 شماره

@app.route('/api/last-message', methods=['GET'])
def get_last_message():
    """دریافت آخرین پیام ذخیره شده"""
    if os.path.exists('last_message.txt'):
        with open('last_message.txt', 'r', encoding='utf-8') as f:
            message = f.read()
        return jsonify({'message': message})
    else:
        # متن پیش‌فرض
        default_message = """⭕️مدیران خودرو ۷۷۷⭕️
با تشکر از ثبت نام شما، کارشناسان ما در اولین فرصت با شما ارتباط برقرار خواهند کرد.

برای اطلاع از شرایط فروش لحظه‌ای مدیران خودرو، پیج اینستاگرام ما را فالو کنید:
https://zaya.io/LeadForm
لغو11"""
        return jsonify({'message': default_message})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """آپلود فایل شماره‌ها"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'فایلی انتخاب نشده'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'فایلی انتخاب نشده'})
    
    if file and file.filename.endswith('.txt'):
        content = file.read().decode('utf-8')
        numbers = [n.strip() for n in content.split('\n') if n.strip()]
        
        with open('dest-numbers.txt', 'w', encoding='utf-8') as f:
            for num in numbers:
                f.write(f"{num}\n")
        
        add_log(f"📁 فایل آپلود شد: {len(numbers)} شماره")
        return jsonify({'success': True, 'count': len(numbers)})
    
    return jsonify({'success': False, 'message': 'فرمت فایل باید txt باشد'})

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    
    if filename == 'processed':
        filepath = 'processed.txt'
    elif filename == 'remaining':
        filepath = 'dest-numbers.txt'
    elif filename == 'message':
        filepath = 'last_message.txt'
    else:
        return jsonify({'success': False, 'message': 'فایل نامعتبر'})
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'success': False, 'message': 'فایل وجود ندارد'})

@app.route('/api/test', methods=['POST'])
def test_connection():
    
    settings = request.json
    
    # اعتبارسنجی
    if 'message' not in settings:
        settings['message'] = "تست اتصال - مدیران خودرو"
    
    test_numbers = ["09123456789"]  
    
    try:
        _, failed = send_sms_batch(
            test_numbers,
            settings['username'],
            settings['password'],
            settings['src_address'],
            settings['message'],
            1
        )
        
        if not failed:
            return jsonify({'success': True, 'message': 'اتصال موفق بود'})
        else:
            return jsonify({'success': False, 'message': 'ارسال ناموفق'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'})

if __name__ == '__main__':
    
    if not os.path.exists('dest-numbers.txt'):
        open('dest-numbers.txt', 'w').close()
    
    if not os.path.exists('processed.txt'):
        open('processed.txt', 'w').close()
    
    if not os.path.exists('last_message.txt'):
        with open('last_message.txt', 'w', encoding='utf-8') as f:
            f.write("""متنی ننوشته اید""")
    
    app.run(debug=True, host='0.0.0.0', port=5000)