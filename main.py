# This program uses code from
# https://platform.openai.com/docs/guides/speech-to-text
# and
# https://platform.openai.com/docs/guides/vision

from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import io
from typing import List
import group5_diagnosis_chatbot.util as group5_diagnosis_chatbot_util
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/diagnosis_chatbot_ye/audio_to_text")
async def audio_to_text_ye(
    voice: UploadFile = File(None),
):
    read_content = await voice.read()
    voice_file = io.BytesIO(read_content)
    voice_file.name = voice.filename

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_YE")
    client = OpenAI(api_key=OPENAI_API_KEY)

    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=voice_file
    )

    return {"response": transcription.text}


@app.post("/diagnosis_chatbot_ye/chat/diagnostic_model/organ")
async def chat_diagnostic_model_organ_ye(
    text: str = Form(None),
    organNames: List[str] = Form(None),
):
    prompt = f"""
    Which item is this text "{text}" about. The item list is here: {organNames}.

    If a match is found, return only one item name in the exact same words as in the list, with "" around the string.

    If no match is found, return only one word none, with "" around the string.

    Only respond the string. Please do not include any other words except the string in your reply.
    """

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_YE")
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "developer", "content": prompt}],
        max_tokens=150,
        temperature=0,
    )

    extracted_info = response.choices[0].message.content.strip()
    response = extracted_info[1:-1]

    return {"response": response}


@app.post("/diagnosis_chatbot_ye/chat/diagnostic_model/model")
async def chat_diagnostic_model_model_ye(
    text: str = Form(None),
    modelNames: List[str] = Form(None),
):
    prompt = f"""
    Which item is this text "{text}" about. The item list is here: {modelNames}.

    If a match is found, return only one item name in the exact same words as in the list, with "" around the string.

    If no match is found, return only one word none, with "" around the string.

    Only respond the string. Please do not include any other words except the string in your reply.
    """

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_YE")
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "developer", "content": prompt}],
        max_tokens=150,
        temperature=0,
    )

    extracted_info = response.choices[0].message.content.strip()
    response = extracted_info[1:-1]

    return {"response": response}


@app.post("/diagnosis_chatbot_ye/chat/gpt")
async def chat_gpt_ye(
    text: str = Form(None),
    user: str = Form(None),
    patient: str = Form(None),
    time: str = Form(None),
    image: UploadFile = File(None),
):
    def format_image_key(data):
        return f"{data["user_id"]}/{data["patient_id"]}/{data["session_time"]}/{data["image_key"]}"

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_YE")
    client = OpenAI(api_key=OPENAI_API_KEY)

    time = time.replace("/", "-")

    data = {
        "user_id": user,
        "patient_id": patient,
        "session_time": time,
        "role": "user",
        "message": text,
        "image_key": image.filename if image is not None else "None",
    }

    if image:
        data["image_key"] = format_image_key(data)
        group5_diagnosis_chatbot_util.upload_content(data, image)
    else:
        group5_diagnosis_chatbot_util.upload_content(data, None)

    contents = group5_diagnosis_chatbot_util.get_contents(user, patient, time)

    history = [
        {
            "role": "developer",
            "content": "You are a helpful assistant.",
        }
    ]

    for row in contents:
        if row["image_key"] == "None":
            history.append(
                {
                    "role": row["role"],
                    "content": row["message"],
                }
            )
        else:
            history.append(
                {
                    "role": row["role"],
                    "content": [
                        {"type": "text", "text": row["message"]},
                        {
                            "type": "image_url",
                            "image_url": {"url": row["image_key"]},
                        },
                    ],
                }
            )

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        temperature=1,
    )
    completion_content = completion.choices[0].message.content

    prompt = f"Speak as an experienced medical professional. Exclude non-technical related content and provide more detail about technical content: {completion_content}"

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "developer", "content": prompt}],
        temperature=1,
    )

    data = {
        "user_id": user,
        "patient_id": patient,
        "session_time": time,
        "role": "assistant",
        "message": completion.choices[0].message.content,
        "image_key": "None",
    }

    group5_diagnosis_chatbot_util.upload_content(data, None)

    return {"response": completion.choices[0].message.content}


@app.post("/diagnosis_chatbot_ye/gpt_past_chats")
async def get_gpt_past_chats_ye(
    user: str = Form(None),
    patient: str = Form(None),
):
    conn = group5_diagnosis_chatbot_util.connect_database("diag_chatbot_db")
    response = group5_diagnosis_chatbot_util.get_sessions_by_user_and_patient(
        conn, user, patient
    )
    conn.close()

    return {"response": response}


@app.post("/diagnosis_chatbot_ye/load_past_chat")
async def load_past_chat_ye(
    user: str = Form(None),
    patient: str = Form(None),
    session: str = Form(None),
):
    return {
        "response": group5_diagnosis_chatbot_util.get_contents(user, patient, session)
    }


@app.post("/diagnosis_chatbot_ye/delete_past_chat")
async def delete_past_chat_ye(
    user: str = Form(None),
    patient: str = Form(None),
    session: str = Form(None),
):
    group5_diagnosis_chatbot_util.delete_contents(user, patient, session)
