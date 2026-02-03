import secrets
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
from dotenv import load_dotenv
import openpyxl
import google.generativeai as old_genai # Keeping old for safety if needed, but primary is new
from google import genai
from google.genai import types
from openpyxl.styles import Alignment
import datetime

load_dotenv()

# Configure Gemini (New SDK)
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GENAI_API_KEY:
    try:
        client = genai.Client(api_key=GENAI_API_KEY)
    except Exception as e:
        print(f"Failed to initialize GenAI Client: {e}")

# Security Configuration
APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "password")
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = APP_USERNAME.encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = APP_PASSWORD.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# File Cleanup Helper
def cleanup_files(file_paths: list[str]):
    """Delete files from the filesystem."""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"Deleted temp file: {path}")
        except Exception as e:
            print(f"Error deleting file {path}: {e}")

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Mount static files (for favicon, manifest, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Directories
TEMP_DIR = "temp"
OUTPUT_DIR = "outputs"
STATIC_DIR = "static"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Load Configuration
with open("mapping_config.json", "r", encoding="utf-8") as f:
    TEMPLATE_CONFIG = json.load(f)

# ... (read_excel_monitoring_data and fill_excel helpers are unchanged) ...

# ... (call_gemini helper is unchanged) ...

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, username: str = Depends(get_current_username)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/templates")
async def get_templates(username: str = Depends(get_current_username)):
    """Return available templates."""
    return TEMPLATE_CONFIG

@app.post("/process")
async def process_data(
    background_tasks: BackgroundTasks,
    template_id: str = Form(...),
    text_input: str = Form(None),
    user_name: str = Form(None),
    user_name_furigana: str = Form(None),
    staff_name: str = Form(None),
    date: str = Form(None),
    location: str = Form(None),
    time: str = Form(None),
    count: str = Form(None),
    next_date: str = Form(None),
    cm_location: str = Form(None),
    cm_time: str = Form(None),
    cm_attendees: str = Form(None),
    cm_service_manager: str = Form(None),
    files: list[UploadFile] = File(None),
    username: str = Depends(get_current_username)
):
    if template_id not in TEMPLATE_CONFIG:
        raise HTTPException(status_code=400, detail="Invalid template ID")
    
    selected_template = TEMPLATE_CONFIG[template_id]
    
    # ... template path logic ... (skip lines 147-160, assuming they are unchanged for now, I need to match context)
    # Actually I should be careful not to delete existing logic. 
    # I will construct the meta_info string first.
    
    # Construct Manual Info String
    manual_info_list = []
    if user_name: manual_info_list.append(f"利用者名 (User Name): {user_name}")
    if staff_name: manual_info_list.append(f"作成担当者 (Staff Name): {staff_name}")
    if date: manual_info_list.append(f"日付 (Date): {date}")
    if location: manual_info_list.append(f"開催場所 (Location): {location}")
    if time: manual_info_list.append(f"時間 (Time): {time}")
    if count: manual_info_list.append(f"回数 (Count): {count}")
    if next_date: manual_info_list.append(f"次回予定 (Next Date): {next_date}")
    # Casemeeting-specific
    if cm_service_manager: manual_info_list.append(f"サービス管理責任者 (Service Manager): {cm_service_manager}")
    if cm_location: manual_info_list.append(f"開催場所 (Location): {cm_location}")
    if cm_time: manual_info_list.append(f"開催時間 (Time): {cm_time}")
    if cm_attendees: manual_info_list.append(f"会議出席者 (Attendees): {cm_attendees}")
    
    manual_info_text = ""
    if manual_info_list:
        manual_info_text = "\n\n【基本情報 (Basic Information provided by User)】\n" + "\n".join(manual_info_list) + "\n"
        # Prioritize manual info
        manual_info_text += "IMPORTANT: Please use the above 'Basic Information' to fill the corresponding fields in the output JSON.\n"

    # Combine with text_input
    full_text_input = (text_input or "") + manual_info_text
    
    # 1. Load Excel Template
    # Template files are expected to be in 'welfare_record_app/template/' 
    # but the config says "template/filename.xlsx", so it depends on CWD.
    # Assuming CWD is 'welfare_record_app'.
    template_source_path = selected_template['filename']
    if not os.path.exists(template_source_path):
         # Try prepending 'template/' or checking relative path
         # Just incase config just has filename
         alt_path = os.path.join("template", os.path.basename(selected_template['filename']))
         if os.path.exists(alt_path):
             template_source_path = alt_path
         else:
             raise HTTPException(status_code=500, detail=f"Template file not found: {template_source_path}")

    # 2. Handle Input Data & Call Gemini
    file_paths = []
    
    try:
        # Save uploaded files
        if files:
            for file in files:
                # Skip empty filenames
                if not file.filename: continue
                
                file_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{file.filename}")
                with open(file_path, "wb") as f:
                    shutil.copyfileobj(file.file, f)
                file_paths.append(file_path)
        
        if not full_text_input and not file_paths:
             raise HTTPException(status_code=400, detail="No input provided (files or text).")

        # Special handling for monitoring_final: extract interim data from uploaded Excel
        interim_data = None
        if template_id == "monitoring_final":
            for fp in file_paths:
                # Check if it's an Excel file
                if fp.endswith('.xlsx') or fp.endswith('.xls'):
                    interim_data = read_excel_monitoring_data(fp)
                    if interim_data:
                        break  # Use first Excel file found
        
        mapping = call_gemini(selected_template, text_input=full_text_input, file_paths=file_paths, interim_data=interim_data)
        
        # --- PRIORITY OVERRIDE START ---
        # Overwrite AI results with Manual Inputs if provided
        if user_name and user_name.strip():
            mapping["利用者氏名"] = user_name
            mapping["氏名"] = user_name # Fallback key
            
        if user_name_furigana and user_name_furigana.strip():
            mapping["利用者氏名_ふりがな"] = user_name_furigana
            mapping["氏名のふりがな"] = user_name_furigana

        if staff_name and staff_name.strip():
            mapping["作成者"] = staff_name
            
        if date and date.strip():
            # Input date is YYYY-MM-DD (e.g. 2026-05-20)
            try:
                dt = datetime.datetime.strptime(date, "%Y-%m-%d")
                mapping["作成年_西暦"] = f"{dt.year}年"
                mapping["作成月"] = f"{dt.month}月"
                mapping["作成日"] = f"{dt.day}日"
                # Fallbacks for other templates
                mapping["作成年月日"] = dt.strftime("%Y年%m月%d日")
                mapping["日付"] = dt.strftime("%Y年%m月%d日")
                mapping["実施日"] = dt.strftime("%Y年%m月%d日")
                # Casemeeting date format
                mapping["開催日（令和〇年〇月〇日）"] = f"令和{dt.year - 2018}年{dt.month}月{dt.day}日"
            except ValueError:
                pass
                
        # Casemeeting-specific priority overrides
        if cm_location and cm_location.strip():
            mapping["開催場所"] = cm_location
            
        if cm_time and cm_time.strip():
            mapping["開催時間"] = cm_time
            
        if cm_attendees and cm_attendees.strip():
            mapping["会議出席者"] = cm_attendees
            
        # Casemeeting uses 利用者様 (with 様)
        if user_name and user_name.strip():
            mapping["利用者様"] = user_name
            
        if cm_service_manager and cm_service_manager.strip():
            mapping["サービス管理責任者"] = cm_service_manager
        # --- PRIORITY OVERRIDE END ---
            
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"AI Processing failed: {str(e)}")
    
    # 3. Fill Excel
    # 3. Fill Excel
    try:
        if mapping:
            mapping['_sheet_name'] = selected_template.get('sheet_name')
        
        # Determine User Name for filename
        user_name_val = "名称未設定"
        possible_keys = ["氏名", "利用者名", "利用者様", "利用者氏名"]
        for key in possible_keys:
            if key in mapping and mapping[key]:
                user_name_val = mapping[key]
                break
        if user_name_val == "名称未設定" and "氏名のふりがな" in mapping:
             user_name_val = mapping["氏名のふりがな"]

        # Date string
        date_str = datetime.datetime.now().strftime("%y.%m.%d")
        template_name = selected_template['name']
        
        # Construct Filename: YY.MM.DD_TemplateName【UserName】.xlsx
        # Ensure safe filename
        safe_user_name = "".join([c for c in user_name_val if c.isalnum() or c in (' ', '　', '_', '-')])
        custom_filename = f"{date_str}_{template_name}【{safe_user_name}】.xlsx"
        
        output_filename = fill_excel(template_source_path, mapping, selected_template['mapping'], output_name=custom_filename)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {str(e)}")

    # Cleanup input files in background
    background_tasks.add_task(cleanup_files, file_paths)

    return {"filename": output_filename}

@app.get("/download/{filename}")
async def download_file(filename: str, background_tasks: BackgroundTasks, username: str = Depends(get_current_username)):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Schedule cleanup of output file after response
    background_tasks.add_task(cleanup_files, [file_path])
    
    return FileResponse(file_path, filename=filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
