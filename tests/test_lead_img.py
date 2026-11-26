"""Lead = ảnh og thật hoặc không ảnh; tiêu đề bọc ngoặc kép được bỏ ngoặc."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import theme, press
assert not theme.real_img({'img': 'img/a.webp', 'img_remote': 'https://opengraph.githubassets.com/1/x/y'})
assert theme.real_img({'img': 'img/a.webp', 'img_remote': 'https://blog.example.com/og.png'})
assert not theme.real_img({})
assert theme.lead_img({'img': 'img/a.webp', 'img_remote': 'https://blog.example.com/og.png'})
assert not theme.lead_img({'img': 'img/a.webp', 'img_remote': 'https://upload.wikimedia.org/x.jpg', 'img_credit': 'A · CC BY · Wikimedia Commons'})
assert press.strip_quotes('"Dario is hyping"') == 'Dario is hyping'
assert press.strip_quotes('“X”') == 'X'
assert press.strip_quotes('"a" and "b"') == '"a" and "b"'
assert press.strip_quotes('Plain') == 'Plain'
print('OK test_lead_img')
