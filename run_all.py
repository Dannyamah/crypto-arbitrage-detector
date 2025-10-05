import multiprocessing
import os
import uvicorn


def run_fastapi():
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")


def run_bot():
    os.system("python main.py")


def run_streamlit():
    os.system("streamlit run app.py")


if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_fastapi)
    p2 = multiprocessing.Process(target=run_bot)
    p3 = multiprocessing.Process(target=run_streamlit)
    p1.start()
    p2.start()
    p3.start()
    p1.join()
    p2.join()
    p3.join()
