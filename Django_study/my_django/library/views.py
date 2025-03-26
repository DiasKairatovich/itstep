from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Book, BorrowRecord
from .forms import ReturnBookForm

def book_list(request):
    books = Book.objects.select_related('author').all()
    borrowed_books = BorrowRecord.objects.filter(returned_at__isnull=True)  # Книги, которые еще не сданы

    if request.method == "POST":
        form = ReturnBookForm(request.POST)
        if form.is_valid():
            borrow_record = form.cleaned_data['book']
            borrow_record.returned_at = timezone.now()
            borrow_record.save()
            return redirect('book_list')

    else:
        form = ReturnBookForm()

    context = {'books': books, 'borrowed_books': borrowed_books, 'form': form}
    return render(request, 'library/book_list.html', context)
