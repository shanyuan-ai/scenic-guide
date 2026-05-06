from django import forms


class WordUploadForm(forms.Form):
    file = forms.FileField(
        label='选择 Word 文件',
        help_text='仅支持 .docx 格式，标题和正文交替排列'
    )