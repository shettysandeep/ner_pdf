"""
Code for Redacting Names using StanfordNERTagger.
PyMUPDF for reading and annotating PDF files.

@author: Sandeep Shetty

Upated : 2/4 To fix redaction over Landscape oriented pages
"""


from nltk.tag.stanford import StanfordNERTagger
import fitz
import string
import nltk
import os
import re
import sys
nltk.download('punkt')

path_st = ('/Users/sandeep/Documents/stanford-ner/')
gzfile = 'english.all.3class.distsim.crf.ser.gz'
jarfile = 'stanford-ner.jar'

st = StanfordNERTagger(path_st + gzfile, path_st + jarfile)


def name_extractor(text):
    """
    Run the Stanford NER tagger to tag the POS of each word in a string.
    Return the tokens tagged as "PERSON" as a generator object.
    """
    name_list = []
    printable = set(string.printable)
    for sent in nltk.sent_tokenize(text):
        new_sent = ''.join(filter(lambda x: x in printable, sent))
        tokens = nltk.tokenize.word_tokenize(new_sent)
        tags = st.tag(tokens)
        for tag in tags:
            if tag[1] == 'PERSON':
                name_list.append(tag[0])
    name_list = set(name_list)
    return name_list


def redact_action(path, op_path):
    """
    Redact the names from a pdf file.
    """
    doc = fitz.open(path)
    #flags = fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE
    all_names = []
    doc_name = doc.name.split("/")[-1]

    print("\n>>> Processing {} <<<\n".format(doc_name))

    # Redacts on Landscape/Potrait Orientation
    for page in doc:
        get_names = name_extractor(page.getText("text"))
        for inames in get_names:
            areas = page.searchFor(inames)
            [page.addRedactAnnot(area, fill = (0, 0, 0)) for area in areas]
        #page.apply_redactions()
        # A piece being tested here - should have branched my git
        redact_annots13 = [annot._get_redact_values() for annot in page.annots()]
        shape = page.newShape()
        for redact in redact_annots13:
            annot_rect = redact["rect"]
            fill = redact["fill"]
            if fill:
                shape.drawRect(annot_rect)  # colorize the rect background
                shape.finish(fill=fill, color=fill)
            if "text" in redact.keys():  # if we also have text
                trect = annot_rect
                fsize = redact["fontsize"]  # start with stored fontsize
                rc = -1
                while rc < 0 and fsize >= 4:  # while not enough room
                    rc = shape.insertTextbox(  # (re-) try insertion
                        trect,
                        redact["text"],
                        fontname=redact["fontname"],
                        fontsize=fsize,
                        color=redact["text_color"],
                        align=redact["align"],
                    )
                    fsize -= 0.5  # reduce font if unsuccessful
                if fsize<1.0:
                    rc = shape.insertTextbox(  # (re-) try insertion
                        trect,
                        redact["text"],
                        fontname=redact["fontname"],
                        fontsize=fsize,
                        color=redact["text_color"],
                        align=redact["align"],
                    )
        shape.commit()
        all_names.append(get_names)

    #~~ TAKE 2:  Redacts on Portrait Orientation Only But Faster
    # To engage Uncomment "Start" to "End"
    # START
    #for page in doc:
    #    dl = page.getDisplayList()
    #    tp = dl.getTextPage(flags)
    #    get_names = name_extractor(tp.extractText())
    #    for inames in get_names:
    #        rlist = tp.search(inames)
    #        for r in rlist:
    #            page.addRedactAnnot(r.rect, fill=(0, 0, 0))
    #            page.apply_redactions()
    #    all_names.append(get_names)
    #~~ END


    # Directories to bifurcate the redacted files from non-redacted ones
    rdctd_fldr = "RDCTD"
    no_rdctn_fldr = "NO_RDCTN"

    rdctd_pth = os.path.join(op_path, rdctd_fldr)
    no_rdctn_pth = os.path.join(op_path, no_rdctn_fldr)

    if not os.path.exists(rdctd_pth):
        os.makedirs(rdctd_pth)

    if not os.path.exists(no_rdctn_pth):
        os.makedirs(no_rdctn_pth)

    # Saving files based on redaction or no redactions made in the file.
    if len(all_names) == 0:
        pdf_name = 'NO_RDCTDN_' + doc_name
        fl_pth = os.path.join(no_rdctn_pth, pdf_name)
        doc.save(fl_pth, garbage=4, deflate=True)
        print('~~~ Saving {} in {} folder ~~~'.format(doc_name, no_rdctn_fldr))
        doc.close()
    else:
        pdf_name = 'RDCTD_' + doc_name
        fl_pth = os.path.join(rdctd_pth, pdf_name)
        doc.save(fl_pth, garbage=4, deflate=True)
        print('~~~ Saving {} in {} folder ~~~'.format(doc_name, rdctd_fldr))
        doc.close()
    return


if __name__ == '__main__':
    #print(os.listdir())
    redact_action('./RDCTD/Dodson- PDSA Cycle #1 -- Plan.pdf', op_path= ".")
    # # Collect all pdf files from a folder to redact.
    # #in_pth = '/Users/sandeep/Documents/1-PROJECTS/gates_ner/data/PDSA_batch1/'
    # op_pth = '/Users/sandeep/Documents/1-PROJECTS/gates_ner/data/testsample/'

    # pdfmatches = []
    # for rt, dnames, fnames in os.walk(in_pth):
    #     for filename in fnames:
    #         if filename.endswith('.pdf'):
    #             pdfmatches.append(os.path.join(rt, filename))

    # # Excluding files in Handwritten folder
    # pdfmatches = [f for f in pdfmatches if not re.search("\/[Hh]andwritten\/", f)]
    # filecount = 0
    # for f in pdfmatches:
    #     redact_action(f, op_pth)
    #     filecount += 1
    # print("\n**** Number of files processed {}".format(filecount))
