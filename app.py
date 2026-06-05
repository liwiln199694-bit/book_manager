import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 設定資料庫：使用內建免安裝的 SQLite，檔案名為 books.db
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'books.db')
# 加入這行，強制 SQLite 處理中文不卡頓
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"check_same_thread": False, "uri": True}
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 定義資料庫欄位 (書籍模型)
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)       # 自動生成的 ID
    title = db.Column(db.String(100), nullable=False)   # 書名 (不可留白)
    author = db.Column(db.String(50), nullable=False)   # 作者
    isbn = db.Column(db.String(20), nullable=True)        # ISBN 碼 (不可重複)
    publisher = db.Column(db.String(120))               # 出版商
    quantity = db.Column(db.Integer, default=1)         # 數量
    translator = db.Column(db.String(50))               # ✨ 新增：譯者欄位

# 建立資料庫檔案 (初次執行時啟動)
with app.app_context():
    db.create_all()

# 路由 1：首頁（顯示書籍清單、以及新增書籍的表單）
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 當使用者按下「新增書籍」提交表單時
        book_title = request.form.get('title')
        book_author = request.form.get('author')
        book_isbn = request.form.get('isbn') or None
        book_publisher = request.form.get('publisher') or None    # 獲取表單的出版社
        book_quantity = request.form.get('quantity')      # 獲取表單的數量
        book_translator = request.form.get('translator') or None  # ✨ 新增：獲取表單的譯者

        # 建立新書籍物件並存入資料庫
        new_book = Book(
            title=book_title, 
            author=book_author, 
            translator=book_translator,  # ✨ 新增：將譯者資料存入資料庫
            isbn=book_isbn,
            publisher=book_publisher,
            quantity=int(book_quantity) if book_quantity else 1
            )
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('index'))
    # --- 以下為搜尋與顯示邏輯的修改 ---
    # 獲取瀏覽器網址列傳過來的搜尋關鍵字 (例如: /?search=哈利波特)
    search_query = request.args.get('search', '')
    
    if search_query:
        # 如果有輸入關鍵字，使用 or_ 條件去多個欄位中進行模糊搜尋 (%關鍵字%)
        from sqlalchemy import or_
        all_books = Book.query.filter(
            or_(
                Book.title.like(f"%{search_query}%"),
                Book.author.like(f"%{search_query}%"),
                Book.publisher.like(f"%{search_query}%"),
                Book.isbn.like(f"%{search_query}%"),
                Book.translator.like(f"%{search_query}%")
            )
        ).all()
    else:
        # 如果沒有關鍵字，就跟原本一樣撈出所有書籍
        all_books = Book.query.all()
        
    return render_template('index.html', books=all_books, search_query=search_query)
    
    # GET 請求：從資料庫撈出所有書籍，傳給前端網頁顯示
    all_books = Book.query.all()
    return render_template('index.html', books=all_books)

# 路由 2：刪除書籍
@app.route('/delete/<int:book_id>')
def delete_book(book_id):
    book_to_delete = Book.query.get_or_404(book_id)
    db.session.delete(book_to_delete)
    db.session.commit()
    return redirect(url_for('index'))
# ✨ 新增：匯出 Excel 功能
@app.route('/export_excel')
def export_excel():
    import pandas as pd
    import io
    from flask import Response

    # 1. 從資料庫撈出所有書籍資料
    all_books = Book.query.all()
    
    # 2. 將資料整理成 Python 字典清單
    books_data = []
    for b in all_books:
        books_data.append({
            "書籍 ID": b.id,
            "書名": b.title,
            "作者": b.author,
            "譯者": b.translator or '-',
            "ISBN": b.isbn or '-',
            "出版社": b.publisher or '-',
            "數量": b.quantity
        })
    
    # 3. 使用 pandas 轉換成 DataFrame 格式
    df = pd.DataFrame(books_data)
    
    # 4. 在記憶體中建立一個 Excel 檔案（不佔用硬體空間）
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='館藏清單')
    output.seek(0)
    
    # 5. 設定瀏覽器下載回應，指定檔名為 book_list.xlsx
    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment;filename=book_list.xlsx"}
    )
if __name__ == '__main__':
    # 加入 port 參數，改為你喜歡的數字（通常建議在 1024 ~ 65535 之間）
    app.run(debug=True, port=1996)