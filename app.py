import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 設定資料庫
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'books.db')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"check_same_thread": False, "uri": True}
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 定義資料庫欄位
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)       
    title = db.Column(db.String(100), nullable=False)   
    author = db.Column(db.String(50), nullable=False)   
    isbn = db.Column(db.String(20), nullable=True)      
    publisher = db.Column(db.String(120))               
    quantity = db.Column(db.Integer, default=1)         
    translator = db.Column(db.String(50))               
    # 預設值設為 '未完成閱讀'
    status = db.Column(db.String(20), nullable=False, default='未完成閱讀') 

with app.app_context():
    db.create_all()

# 路由 1：首頁
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        book_title = request.form.get('title')
        book_author = request.form.get('author')
        book_isbn = request.form.get('isbn') or None
        book_publisher = request.form.get('publisher') or None    
        book_quantity = request.form.get('quantity')      
        book_translator = request.form.get('translator') or None  

        # 新增書籍時，不從表單拿狀態，直接使用預設的 '未完成閱讀'
        new_book = Book(
            title=book_title, 
            author=book_author, 
            translator=book_translator,  
            isbn=book_isbn,
            publisher=book_publisher,
            quantity=int(book_quantity) if book_quantity else 1,
            status='未完成閱讀' 
        )
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('index'))
        
    search_query = request.args.get('search', '')
    if search_query:
        from sqlalchemy import or_
        all_books = Book.query.filter(
            or_(
                Book.title.like(f"%{search_query}%"),
                Book.author.like(f"%{search_query}%"),
                Book.publisher.like(f"%{search_query}%"),
                Book.isbn.like(f"%{search_query}%"),
                Book.translator.like(f"%{search_query}%"),
                Book.status.like(f"%{search_query}%")
            )
        ).all()
    else:
        all_books = Book.query.all()
        
    return render_template('index.html', books=all_books, search_query=search_query)

# ✨ 新增路由：點擊更新/切換閱讀狀態
@app.route('/toggle_status/<int:book_id>')
def toggle_status(book_id):
    book = Book.query.get_or_404(book_id)
    # 如果原本是未完成，就改成已完成；反之亦然
    if book.status == '未完成閱讀':
        book.status = '已完成閱讀'
    else:
        book.status = '未完成閱讀'
    db.session.commit()
    return redirect(url_for('index'))

# 路由 2：刪除書籍
@app.route('/delete/<int:book_id>')
def delete_book(book_id):
    book_to_delete = Book.query.get_or_404(book_id)
    db.session.delete(book_to_delete)
    db.session.commit()
    return redirect(url_for('index'))

# 匯出 Excel 功能（維持不變，會自動依據最新狀態切換 V 記號）
@app.route('/export_excel')
def export_excel():
    import pandas as pd
    import io
    from flask import Response
    from datetime import datetime
    import openpyxl
    from openpyxl.styles import Font, Alignment

    # 1. 從資料庫撈出所有書籍資料
    all_books = Book.query.all()
    
    books_data = []
    for b in all_books:
        books_data.append({
            "書籍 ID": b.id,
            "書名": b.title,
            "作者": b.author,
            "譯者": b.translator or '-',
            "出版社": b.publisher or '-',
            "ISBN": b.isbn or '-',
            "數量": b.quantity,
            "未完成閱讀": "V" if b.status == "未完成閱讀" else "", 
            "已完成閱讀": "V" if b.status == "已完成閱讀" else ""  
        })
    
    # 2. 轉換成 DataFrame
    df = pd.DataFrame(books_data)
    
    # 3. 建立一個全新的 openpyxl 工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "館藏清單"
    
    # 顯示網格線
    ws.views.sheetView[0].showGridLines = True

    # 4. 寫入左上角的標題 (A1)
    ws['A1'] = "Gary的圖書管理資料"
    ws['A1'].font = Font(size=16, bold=True)

    # 5. 寫入右上角的匯出日期 (I1)
    today_str = f"匯出日期: {datetime.now().strftime('%Y-%m-%d')}"
    ws['I1'] = today_str
    ws['I1'].font = Font(size=10, italic=True)
    ws['I1'].alignment = Alignment(horizontal='right')

    # 6. 從第 3 行（Row 3）開始寫入資料表頭
    headers = list(df.columns)
    ws.append([]) # 第 2 行：留空行
    ws.append(headers) # 第 3 行：寫入表頭

    # 7. 寫入所有資料內容
    for row in df.values.tolist():
        ws.append(row)

    # 8. 將活頁簿儲存到記憶體中並導出
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment;filename=book_list.xlsx"}
    )

if __name__ == '__main__':
    app.run(debug=True, port=1996)