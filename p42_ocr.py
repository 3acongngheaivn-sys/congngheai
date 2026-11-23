"""P42 conservative offline multi-view OCR. Does not modify the source image.
The optional RapidOCR model must be provisioned by the Windows packaging workflow.
"""
import threading
import unicodedata
from collections import defaultdict
import numpy as np
import cv2
from PIL import Image, ImageOps
import p38_image as p38
import p63_geometry as geometry
import p66_cleanup

_engine = None
_engine_lock = threading.Lock()
_engine_failure = None

def clean(value):
    return unicodedata.normalize('NFC', ' '.join(str(value or '').split()))

def suspicious(value):
    value = clean(value)
    letters = [c for c in value if c.isalpha()]
    return len(letters) < 3 or (len(letters) < 5 and len(value.split()) > 1)

def variants(image):
    """Bounded image variants; preserve RGB for colored/stroked lettering."""
    image = ImageOps.exif_transpose(image).convert('RGB')
    a = np.asarray(image)
    h, w = a.shape[:2]
    if max(h,w) > 2200:
        scale = 2200/max(h,w)
        a = cv2.resize(a,(max(1,round(w*scale)),max(1,round(h*scale))),interpolation=cv2.INTER_AREA)
    yield 'GỐC RGB', Image.fromarray(a)
    # The original RGB is always tested first. Geometry is optional and conservative.
    corrected,projective,rotated=geometry.correct(Image.fromarray(a),p38.estimate_text_skew)
    if projective or rotated:
        yield 'CHỈNH THẲNG RGB',corrected
    # Keep each PA available for OCR as an alternative, not as the sole input.
    try:
        for index,(_,name,mask) in enumerate(p38.five_methods(Image.fromarray(a))):
            if index>=7:break
            view=p38.method_image(mask,index).convert('RGB')
            yield 'PA%d'%(index+1),view
            cleaned=p66_cleanup.clean_mask(mask)
            if not np.array_equal(cleaned,(np.asarray(mask)>0).astype(np.uint8)):
                yield 'PHƯƠNG ÁN %d - ĐÃ LỌC NHIỄU'%(index+1),p38.method_image(cleaned,index).convert('RGB')
    except Exception:
        pass
    lab = cv2.cvtColor(a,cv2.COLOR_RGB2LAB)
    light = lab[:,:,0]
    clahe = cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(light)
    lab[:,:,0] = clahe
    yield 'TƯƠNG PHẢN CỤC BỘ', Image.fromarray(cv2.cvtColor(lab,cv2.COLOR_LAB2RGB))
    gray = cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
    if gray.shape[0] >= 25 and gray.shape[1] >= 25:
        # Both polarities are useful for white letters and dark text.
        _,bw = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        yield 'ĐEN TRẮNG',Image.fromarray(cv2.cvtColor(bw,cv2.COLOR_GRAY2RGB))
        yield 'ĐẢO ĐEN TRẮNG',Image.fromarray(cv2.cvtColor(255-bw,cv2.COLOR_GRAY2RGB))

def _rapid_engine():
    global _engine, _engine_failure
    if _engine is not None:return _engine
    if _engine_failure is not None:return None
    try:
        from rapidocr import RapidOCR
        # Model deployment is managed separately; avoid assuming a model exists.
        _engine = RapidOCR(params={
            'Det.ocr_version':'PP-OCRv6','Rec.ocr_version':'PP-OCRv6',
            'Det.lang_type':'vi','Rec.lang_type':'vi',
            'Det.model_type':'small','Rec.model_type':'small'})
        return _engine
    except Exception as exc:
        _engine_failure = str(exc)[:140]
        return None

def _deep(image):
    engine = _rapid_engine()
    if engine is None:return None,0.0
    try:
        # RapidOCR engine may not be thread safe: serialize calls.
        with _engine_lock:
            result = engine(np.asarray(image))
        texts = getattr(result,'txts',None)
        scores = getattr(result,'scores',None)
        if texts is None and isinstance(result,tuple) and result:
            texts=[x[1] for x in result[0] if len(x)>1] if result[0] else []
            scores=[x[2] for x in result[0] if len(x)>2] if result[0] else []
        if not texts:return None,0.0
        confidence=float(np.mean(scores)) if scores is not None and len(scores) else 0.0
        return clean(' '.join(texts)),confidence
    except Exception:
        return None,0.0

def recognize(image,legacy):
    """Return (text, engine, needs_review). Never invent missing Vietnamese accents.

    Automatic acceptance requires strong confidence AND agreement from another
    independent OCR engine. Image variants from the same model do not count as
    independent votes.
    """
    image=ImageOps.exif_transpose(image).convert('RGB')
    samples=list(variants(image))
    reads=[]
    weak_reads=[]
    for label,view in samples:
        text,confidence=_deep(view)
        if text:
            entry=(text,confidence,'RapidOCR '+label)
            (weak_reads if suspicious(text) else reads).append(entry)
    # Legacy Tesseract is independent; include corrected RGB when available.
    for label,view in samples[:3]:
        try:
            text,engine=legacy(view)
            text=clean(text)
            if text:
                entry=(text,0.0,'Tesseract '+label)
                (weak_reads if suspicious(text) else reads).append(entry)
        except Exception:
            continue
    if not reads:
        # User requested automatic fill, including doubtful OCR. Never invent text.
        if weak_reads:
            choice=max(weak_reads,key=lambda e:(e[1],len(e[0])))
            return choice[0],choice[2]+' • CẦN KIỂM TRA',True
        return None,'Không nhận được ký tự',True
    groups=defaultdict(list)
    for entry in reads:groups[entry[0].casefold()].append(entry)
    def group_rank(g):
        independent=len({e[2].split()[0] for e in g})
        return (independent, max(e[1] for e in g),len(g))
    ranked=sorted(groups.values(),key=group_rank,reverse=True)
    best=ranked[0]
    selected=max(best,key=lambda e:e[1])
    has_rapid=any(e[2].startswith('RapidOCR') for e in best)
    has_tesseract=any(e[2].startswith('Tesseract') for e in best)
    strong=any(e[1]>=0.85 for e in best)
    accepted=has_rapid and has_tesseract and strong and not suspicious(selected[0])
    return selected[0], (' + '.join(sorted(set(e[2].split()[0] for e in best))) +
                         ' • '+str(len(best))+' lượt trùng khớp'), not accepted


def recognize_single(image,legacy):
    """Run both OCR engines on exactly the edited bitmap, with no variants."""
    image=ImageOps.exif_transpose(image).convert('RGB')
    deep,conf=_deep(image)
    try:
        tess,_=legacy(image)
    except Exception:
        tess=None
    deep=clean(deep);tess=clean(tess)
    if deep and tess and deep.casefold()==tess.casefold():
        return deep,'RapidOCR + Tesseract • ẢNH CHỈNH SỬA',conf<0.85
    if deep:return deep,'RapidOCR • ẢNH CHỈNH SỬA • CẦN KIỂM TRA',True
    if tess:return tess,'Tesseract • ẢNH CHỈNH SỬA • CẦN KIỂM TRA',True
    return None,'Không nhận được ký tự trong ảnh chỉnh sửa',True
