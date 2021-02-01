from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, copy_current_request_context
import os
from .parser import Parser

app = Flask(__name__, template_folder='templates')
app.config['SERVER_NAME'] = "127.0.0.1:5000"
app.secret_key = "put_some_rnd_secret_key"

# В задании не была оговорена валидация ссылки и уровня, но
# пусть эти функции будут её иммитировать

def is_url_valid(url):
    '''Проверка, валидный ли url'''
    return True

def is_level_valid(level):
    '''Проверка на уровень вложенности, он должен быть больше 0'''
    return True

@app.route("/download_page", methods=['POST', 'GET'])
def download_page():
    '''Страница, где по ссылке можно скачать архив'''
    return render_template("download.html", zip_filename=session['zip_filename'])

@app.route('/processing', methods=['GET'])
def parse_url(url, lvl):
    '''Спарсить url и вернуть ссылку на скачивание'''
    with app.test_request_context('/download_page'):
        _parser = Parser(url, lvl)
        link = _parser.start()
        return link

@app.route("/parse", methods=['POST'])
def parse():
    '''ВЗять данные формы, валидация и начало алгоритма'''
    url = request.form['url']
    lvl = request.form['inner_level']
    if is_url_valid(url) and is_level_valid(lvl):

        if "http" not in url:
            url = "http://" + url

        # можно потом parse_url закинуть в отдельный поток
        session["zip_filename"] = os.path.join(app.root_path, parse_url(url, int(lvl)))

        return redirect(url_for("download_page"))
    else:
        return "Неверная ссылка или уровень валидации. <a href='../'>Вернуться</a>"


@app.route('/', methods=['post', 'get'])
def hello_world():
    '''Корневая страница'''
    return render_template("index.html")


if __name__ == '__main__':
    app.run(threaded=True)
