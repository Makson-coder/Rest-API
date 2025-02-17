from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from uuid import uuid4
from PIL import Image
import os
import mimetypes
import time
from time import sleep

#инициализация FastAPI
app = FastAPI()

#Каталоги для хранения загружаемых файлов и миниатюр
UPLOAD_DIRECTORY = "./uploads/"
THUMBNAIL_DIRECTORY = "./thumbnails/"


# Создаем необходимые каталоги, если они отсутствуют. 
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
os.makedirs(THUMBNAIL_DIRECTORY, exist_ok=True)


#Функция для создания кадра из видео с помощью FFmpeg.
# video_path: Путь к исходному видеофайлу.
# output_path: Путь для сохранения кадра.
def ffmpeg(file_path_vid: str ,file_path_save: str):
    #ss 00:00:05 указывает время начала извлечения (5 секунд).
    # -vframes 1 указывает количество извлекаемых кадров (1 кадр).
    # -y перезаписывает существующий файл, если он есть.
    ff = "ffmpeg -i " + file_path_vid +" -ss 00:00:05 -vframes 1 "+file_path_save+" -y"
    os.system(ff)


#Ручка для загрузки файла и получение инфо. о файле
@app.put("/api/files/")
async def upload_file(file: UploadFile = File(...)):
    # Генерируем UUID для файла
    file_id = uuid4()
    # Формируем полный путь к файлу
    file_path = os.path.join(UPLOAD_DIRECTORY, f"{file_id}_{file.filename}")
    # Читаем файл
    contents = await file.read()
    # Записываем файл
    with open(file_path, "wb") as f:
        f.write(contents)
    # Получаем размера файла
    file_size = os.path.getsize(file_path)
    #Определяем mimetype файла
    mimetype = mimetypes.guess_type(file_path)
    #Проверяем, файл картинка или видео
    if ("image" in mimetype[0]) or ("video" in mimetype[0]): 
    # Возвращение информации о файле
       return {"uuid": str(file_id), "size": file_size, "mime": mimetype[0]} #если файл видео или картинка
    else:
       raise HTTPException(status_code=500,detail="File is not an image or video") #если файл не видео или картинка
       return {"File is not an image or video"}

#Ручка для возвращения миниатюр
@app.put("/api/files/{file_uuid}")
#file_uuid: UUID файла, width: Ширина миниатюры (опционально), length: Длина миниатюры (опционально), return: FileResponse с файлом или миниатюрой.
async def update_item(file_uuid: str, length: int | None = None, width: int | None = None ):
    #Проверяем, содержится ли UUID файла в имени файла перебором for
    #рассматриваем случай без создания миниаютр (None в размерах)
    k = 0
    #Проверяем наличие параметров миниатюр (высота ширина)
    if (width == None) and (length == None): 
        for filename in os.listdir(UPLOAD_DIRECTORY): #перебираем файлы из папки UPLOAD_DIRECTORY
            if file_uuid in filename: #сравниваем uuid присланный и которые находятся в папке
                k = k + 1 
                mime = mimetypes.guess_type(f"{UPLOAD_DIRECTORY}/{filename}") #узнаем тип файла 
                if "image" in mime[0]: #cлучай с фото
                    return FileResponse(f"{UPLOAD_DIRECTORY}/{filename}")
                if "video" in mime[0]: #случай с видео
                    full_path_video = f"{UPLOAD_DIRECTORY}{filename}" #определяем путь к видео
                    file_path_frame = os.path.join(THUMBNAIL_DIRECTORY, f"frame_{file_uuid}.png") #путь к кадру
                    ffmpeg(full_path_video, file_path_frame) #запускаем ffmpeg для обработки видео
                    sleep(5) #ждем
    
    #случай когда присутствует в запросе один параметр
    if ((width == None) and (length != None)) or (((width != None) and (length == None))):
        if ((width == None) and (length != None)):
           raise HTTPException(status_code=500,detail="Width parameter not specified") #высылаем ошибку
           #return {"width parameter not specified"} #записываем комментарий в файл
        if ((width != None) and (length == None)):
           raise HTTPException(status_code=500,detail="Length parameter not specified")
           #return {"Length parameter not specified"}
       
    #случай когда присутствует в запросе оба параметра
    if (width != None) and (length != None):
        for filename in os.listdir(UPLOAD_DIRECTORY):
            if file_uuid in filename:
                mime = mimetypes.guess_type(f"{UPLOAD_DIRECTORY}/{filename}") #проверяем тип файла
                if "image" in mime[0]:
                    #фиксируем путь к файлу миниатюры
                    file_path_mini = os.path.join(THUMBNAIL_DIRECTORY, f"mini_{filename}")
                    #фиксируем путь к исходному файлу
                    filename_full = f"{UPLOAD_DIRECTORY}/{filename}"
                    try: #пробуем создать миниатюру
                        with Image.open(filename_full) as img: #делаем сокращение
                            img.thumbnail((length,width)) #создаем миниатюру
                            img.save(file_path_mini) #записываем миниатюру
                            return FileResponse(file_path_mini) #возвращаем файл
                    except Exception as e: #высылаем ошибку в случае неудачи
                        raise HTTPException(status_code=500,detail="Could not create thumbnail.")
                if "video" in mime[0]:
                    full_path_video = f"{UPLOAD_DIRECTORY}{filename}" #путь к видео
                    file_path_frame = os.path.join(THUMBNAIL_DIRECTORY, f"frame_{file_uuid}.png") #путь к кадру
                    ffmpeg(full_path_video, file_path_frame) #запускаем ffmpeg
                    sleep(5) #выжидаем для сознания 
                    try: #пробуем выполнить 
                        with Image.open(file_path_frame) as img: #делаем сокращение
                            img.thumbnail((length,width)) #создаем миниатюру
                            img.save(file_path_frame) #записываем файл
                            return FileResponse(file_path_frame) #возвращаем файл
                    except Exception as e:
                        raise HTTPException(status_code=500,detail="Could not create thumbnail.") #возращаем ошибку в случае неудачи 
                    return FileResponse(file_path_frame)
    if k == 1:
        return FileResponse(file_path_frame) #отправляем файл
    else:
        raise HTTPException(status_code=500,detail="File not found") #если нет такого файла

