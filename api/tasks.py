import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ET

from celery import shared_task
from celery.utils.log import get_task_logger

from .logging.ErrorTypes import (WRInlineStructureError, WREndStructureError, MSInlineStructureError, MSEndStructureError, ORDInlineStructureError, ORDEndStructureError, MCInlineStructureError, MCEndStructureError, TFInlineStructureError, TFEndStructureError, FIBInlineStructureError, FIBEndStructureError, MATInlineStructureError, MATEndStructureError, InlineNoTypeError, EndAnswerNoTypeError, NoTypeDeterminedError, MarkDownConversionError)
from .logging.WarningTypes import (RespondusTypeEWarning, RespondusTypeMRWarning, RespondusTypeFMBWarning, RespondusTypeMTWarning)

from .logging.logging_adapter import FilenameLoggingAdapter
from .models import EndAnswer, Question, QuestionLibrary
from .process.process_helper import (add_error_message, add_warning_message, html_to_plain, markdown_to_plain, markdown_to_html, trim_md_to_html, trim_text)
from .process.questionbuilder.fib import build_endanswer_FIB, build_inline_FIB
from .process.questionbuilder.matching import (build_endanswer_MAT, build_inline_MAT)
from .process.questionbuilder.multiplechoice import (build_endanswer_MC, build_inline_MC)
from .process.questionbuilder.multipleselect import (build_endanswer_MS, build_inline_MS)
from .process.questionbuilder.ordering import (build_endanswer_ORD, build_inline_ORD)
from .process.questionbuilder.truefalse import (build_endanswer_TF, build_inline_TF)
from .process.questionbuilder.writtenresponse import (build_endanswer_WR_with_list, build_inline_WR_with_keyword, build_inline_WR_with_list)

logger = logging.getLogger(__name__)
loggercelery = get_task_logger(__name__)

def check_inline_questiontype(question, answers, wr_answer):
    questionlibrary = question.section.question_library
    logger = FilenameLoggingAdapter(loggercelery, {
        'filename': questionlibrary.temp_file.name,
        'user_ip': questionlibrary.user_ip
        })
    answers_length = len(answers)
    marked_answers_count = 0
    unmarked_answers_count = 0
    matching_answers_count = 0
    KeywordTrueFound = False
    KeywordFalseFound = False

    is_fib = re.search(r"\[(.*?)\]", question.text)

    if answers_length == 0:
        if is_fib:
            # ====================  FIB confirmed  ====================
            logger.debug("Question Type determined: inline_FIB")   
            return 'inline_FIB'
        
        if wr_answer != None:
            # ====================  WR confirmed  ====================
            logger.debug("Question Type determined: inline_WR_keyword")   
            return 'inline_WR_keyword'

    for answer in answers:
        # answer_text = markdown_to_plain(answer.find('content').text.lower())
        answer_text = markdown_to_plain(answer.get("answer_content").lower())
        answer_text = trim_text(answer_text)
        is_correct = answer.get('correct')
        if is_correct:
            marked_answers_count += 1
        if not is_correct:
            unmarked_answers_count += 1

        if answer_text == 'true':
            KeywordTrueFound = True

        if answer_text == 'false':
            KeywordFalseFound = True
        matching_answers = re.search(r"(.*)=(.*)", answer_text)

        if matching_answers is not None:
            matching_answers_count += 1
        
    if answers_length == 2 and KeywordTrueFound == True and KeywordFalseFound == True:
        # ====================  TF confirmed  ====================
        logger.debug("Question Type determined: inline_TF")   
        return 'inline_TF'

    if marked_answers_count == 1 and (question.questiontype != 'MS' and question.questiontype != 'MR'):
        # ====================  MC confirmed  ====================
        logger.debug("Question Type determined: inline_MC")   
        return 'inline_MC'

    if marked_answers_count > 1 or (question.questiontype == 'MS' or question.questiontype == 'MR'):
        # ====================  MS confirmed  ====================
        logger.debug("Question Type determined: inline_MS")   
        return 'inline_MS'

    if matching_answers_count == answers_length and matching_answers_count > 1 :
        # ====================  MAT confirmed  ====================
        logger.debug("Question Type determined: inline_MAT")   
        return 'inline_MAT'

    if (unmarked_answers_count == 1 and answers_length == 1) or (question.questiontype == 'WR' or question.questiontype == 'E'):
        # ====================  WR confirmed  ====================
        logger.debug("Question Type determined: inline_WR_list")   
        return 'inline_WR_list'

    if answers_length > 0 and unmarked_answers_count == answers_length:
        # ====================  ORD confirmed  ====================
        logger.debug("Question Type determined: inline_ORD")   
        return 'inline_ORD'
    logger.debug("Question Type determined: inline_NO_TYPE")   
    return 'inline_NO_TYPE'


def check_endanswer_questiontype(question, answers, endanswer):
    answers_length = len(answers)
    endanswer_text = markdown_to_plain(endanswer.answer.lower())
    endanswer_text = trim_text(endanswer_text)

    if answers_length > 0:
        # possible TF, MC, MS
        answer_list = list(map(str.strip, endanswer_text.split(',')))
        answer_key_length = len(answer_list)
        KeywordTrueFound = False
        KeywordFalseFound = False
    
        for answer in answers:
            answer_text = markdown_to_plain(answer['answer_content'].lower())
            answer_text = trim_text(answer_text)

            for choice_answer in answer_list:
                correctanswer_index =  (ord(choice_answer)-97)
                
                if correctanswer_index <= (answers_length-1):
                    # answer index exist
                    pass
                else:
                    return 'endanswer_NO_TYPE'


            if answer_text == 'true':
                KeywordTrueFound = True

            if answer_text == 'false':
                KeywordFalseFound = True
        
        if answers_length == 2 and KeywordTrueFound == True and KeywordFalseFound == True:
            # ====================  TF confirmed  ====================
            return 'endanswer_TF'
            
        if answer_key_length == 1 and (question.questiontype != 'MS' and question.questiontype != 'MR'):
            # ====================  MC confirmed  ====================
            return 'endanswer_MC'

        if (question.questiontype == 'MS' or question.questiontype == 'MR') or answer_key_length > 1:
            # ====================  MS confirmed  ====================
            return 'endanswer_MS'
    
    else:
        # possible FIB, MAT, ORD, WR
        matching_answers_count = 0
        is_fib = re.findall(r"\[(.*?)\]", question.text)
        answer_list = list(map(str.strip, endanswer_text.split(';')))
        answer_key_length = len(answer_list)
        for answer in answer_list:
            matching_answer = re.search(r"(.*)=(.*)", answer)

            if matching_answer is not None:
                matching_answers_count += 1
        
        if matching_answers_count == answer_key_length and matching_answers_count > 1 :
            # =========================  MAT confirmed =======================
            return 'endanswer_MAT'
            
        if len(is_fib) == answer_key_length:
            # =========================  FIB confirmed =======================
            return 'endanswer_FIB'

        if answer_key_length > 1:
            # =========================  ORD confirmed =======================
            return 'endanswer_ORD'

        if answer_key_length == 1:
            # =========================  WR confirmed =======================
            return 'endanswer_WR'

    return 'endanswer_NO_TYPE'

@shared_task()
def parse_question(question_id, endanswer=None):

    question = Question.objects.get(pk=question_id)
    questionlibrary = question.section.question_library
    is_random = questionlibrary.randomize_answer
    enumeration = questionlibrary.enumeration 
    logger = FilenameLoggingAdapter(loggercelery, {
        'filename': questionlibrary.temp_file.name,
        'user_ip': questionlibrary.user_ip
        })

    try:
        endanswer = EndAnswer.objects.get(pk=endanswer)
    except EndAnswer.DoesNotExist:
        logger.info("No End answer found")

    os.chdir('/antlr_build/questionparser')
    popen = subprocess.Popen(
        'java -cp questionparser.jar:* questionparser', 
        shell=True,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE
        )
    result, errors = popen.communicate(input=question.raw_content.encode("utf-8"))
    popen.stdout.close()
    return_code = popen.wait()
    os.chdir('/code')
    question.parser_output_xml = result.decode("utf-8")
    question.save()

    root = None
    try:
        root = ET.fromstring(result.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Empty question: {question.id}")
        return "Empty question: " + str(e) + errors

# ================================# ================================
#   GET QUESTION DATA FROM XML
# ================================# ================================
    wr_answer = None
    try:
        questiontype = root.find('type')
        if questiontype is not None:
            question.questiontype = trim_text(questiontype.text)

        title = root.find('title')
        if title is not None:
            title_text = markdown_to_plain(title.text)
            title_text = title_text.replace('\n', ' ')
            question.title = trim_text(title_text)

        points = root.find('points')
        if points is not None:
            filterpoint = re.search("\d+((.|,)\d+)?", points.text)
            question.points = float(filterpoint.group())

        randomize = root.find('randomize')
        if randomize is not None:
            is_randomize = trim_text(randomize.text).lower() in ['yes', 'true']
            is_random = is_random or is_randomize

        question_body = root.find("question_body")
        if question_body is None:
            raise Exception("Question_body empty")

        question_body_part_list = question_body.findall("question_body_part")
        if question_body_part_list is None:
            raise Exception("Question_body empty")
        
        wr_answer = root.find("wr_answer")

    except Exception as e:  
        logger.error(f"Failed to get question data from xml > {str(e)}") 
        return "#" + str(question.number_provided) + " " + str(e)

    try:
        # save question number that was provided
        question_number = question_body_part_list[0].find('prefix')
        if question_number is not None:
            filter_question_number = re.search("\d+", question_number.text)
            question.number_provided = filter_question_number.group()
            question.save()
        # logger.debug("Finished getting question number")
    except Exception as e:
        logger.error(f"getting question number > {str(e)}")
        return "#" + str(question.number_provided) + " " + str(e)

    answer_list = []
    part_of_question_list = []
    try:
        # logger.debug( f"#{str(question.number_provided)} Starting splitting body_part into question_content and answers block")
        # only if there are multiple question_body parts then proceed to splitting
        if (len(question_body_part_list) == 1) and (question_body_part_list[0].get('prefix_type') == 'NUMLIST_PREFIX'):
            part_of_question_list.append(question_body_part_list[0])
        elif (len(question_body_part_list) == 2) and (question_body_part_list[0].get('prefix_type') == 'NUMLIST_PREFIX') and (question_body_part_list[1].get('prefix_type') == 'FEEDBACK'):
            # Case of WR or FIB question with feedback and using answer key
            part_of_question_list.append(question_body_part_list[0])
            part_of_question_list.append(question_body_part_list[1])
        else:
            # Filter out the last letter enumerated list so that it can be set as the answerlist
            start_of_list_found = False
            # Start iterating from the last item going up untill the index "a" is found and continue adding the rest of the lists as question content
            for question_body_part in reversed(question_body_part_list):
                if not start_of_list_found and (wr_answer == None):
                    answer_list.append(question_body_part)
                else:
                    part_of_question_list.append(question_body_part)
                if question_body_part.get('prefix_type') == "LETTERLIST_PREFIX" or question_body_part.get('prefix_type') == "CORRECT_ANSWER":
                    check_index = ''.join(filter(str.isalpha, question_body_part.find('prefix').text.lower()))
                    if check_index == "a":
                        start_of_list_found = True
            # because we started from the last item we need to reverse the list to bring in correct order
            answer_list = answer_list[::-1]
            part_of_question_list = part_of_question_list[::-1]
        # logger.debug( f"#{str(question.number_provided)} Finished plitting body_part into question_content and answers block")
    except Exception as e:
        logger.error(f"splitting body_part into question_content and answers block > {str(e)}")
        return "#" + str(question.number_provided) + " " + str(e)

    answers = []
    try:
        # Combine feedback and answers 
        # Check if first item is LETTERLIST_PREFIX or CORRECT_ANSWER
        if (answer_list[0].get('prefix_type') == "LETTERLIST_PREFIX" or answer_list[0].get('prefix_type') == "CORRECT_ANSWER"):
            # raise Exception("First item in Answer list is not a Letterlist item")
            for answer in answer_list:
                if answer.get('prefix_type') == "LETTERLIST_PREFIX":
                    current_answer = {
                        "answer_prefix": answer.find('prefix').text,
                        "answer_content": answer.find('content').text,
                        "correct": False,
                        "feedback": None
                        }
                    answers.append(current_answer)
                elif answer.get('prefix_type') == "CORRECT_ANSWER":
                    current_answer = {
                        "answer_prefix": answer.find('prefix').text,
                        "answer_content": answer.find('content').text,
                        "correct": True,
                        "feedback": None
                        }
                    answers.append(current_answer)
                elif answer.get('prefix_type') == "NUMLIST_PREFIX":
                    current_answer = answers.pop()
                    current_answer.update({"content": current_answer.get("content") + answer.find('content').text})
                    answers.append(current_answer)
                elif answer.get('prefix_type') == "FEEDBACK":
                    current_answer = answers.pop()
                    current_answer.update({"feedback": answer.find('content').text})
                    answers.append(current_answer)
                elif answer.get('prefix_type') == "HINT":
                    continue
        # logger.debug( f"#{str(question.number_provided)} Finished combining answer block elements items into answers")
    except Exception as e:
        logger.error(f"#{str(question.number_provided)} Combining answer block elements items into answers > {str(e)}")

    try:
        # logger.debug( f"#{str(question.number_provided)} Start combining question content, any lists, feedback and hint in one dict")
        # Combine question content, any lists, feedback and hint in one dict 
        question_from_xml = {
            "question_content": "",
            "feedback": "",
            "hint": ""
            }        
        for index, question_content_item in enumerate(part_of_question_list):
            if question_content_item.get('prefix_type') == "FEEDBACK":
                question_from_xml.update({"feedback": question_content_item.find('content').text})
            elif question_content_item.get('prefix_type') == "HINT":
                question_from_xml.update({"hint": question_content_item.find('content').text})
            else:
                question_content = question_from_xml.get("question_content")
                question_content_to_append = ""
                if index > 0:
                    question_content_to_append = question_content_item.find('prefix').text
                question_content_to_append = question_content_to_append + question_content_item.find('content').text
                question_from_xml.update({"question_content": question_content + question_content_to_append})

        # logger.debug( f"#{str(question.number_provided)} Finished combining question content, any lists, feedback and hint in one dict")
    except Exception as e:
        logger.error(f"#{str(question.number_provided)} Combining question content, any lists, feedback and hint in one dict {str(e)}")

    question_feedback = trim_md_to_html(question_from_xml.get("feedback"))
    if question_feedback is not None:
        question.feedback = trim_md_to_html(question_feedback)
    question_hint = trim_md_to_html(question_from_xml.get("hint"))
    if question_hint is not None:
        question.hint = trim_md_to_html(question_hint)
    
    logger.debug(question_from_xml)


        # test questionlib

        # logger.debug("testing question lib")

        # ql = question.section.question_library
        # logger.debug(ql.temp_file)








    # Re-init logging adapter with available question number 

    logger = FilenameLoggingAdapter(loggercelery, {
        'filename': questionlibrary.temp_file.name,
        'user_ip': questionlibrary.user_ip,
        'question': str(question.number_provided)
        })

# ================================# ================================
#   CHECK TYPES AND BUILD QUESTION
# ================================# ================================
 
    try:
        if question_from_xml is not None:
            question_text = trim_md_to_html(question_from_xml.get("question_content"))
            question.text = question_text
            question.save()
    except Exception as e:
        return str(question.number_provided) + " " + str(e) 


# ================================# ================================
#   Written Response
# ================================# ================================
    question_type = None

    try:
        if question.questiontype == 'WR' or question.questiontype == 'E':
            try:
                if question.questiontype == 'E':
                    warning_message = 'Respondus format "Type: E" was found on the file. Please use "Type: WR" instead.'
                    add_warning_message(question, warning_message)
                    raise RespondusTypeEWarning(question.warning)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)
            
            try:
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)

                    if question_type == 'inline_WR_keyword':
                        build_inline_WR_with_keyword(question, wr_answer)
                    elif question_type == 'inline_WR_list':
                        build_inline_WR_with_list(question, answers)
                    else:
                        error_message = "Inline question structure doesn't conform to WR type question format."
                        add_error_message(question, error_message)
                        raise WRInlineStructureError(question.error)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)

                    if question_type == 'endanswer_WR':
                        build_endanswer_WR_with_list(question, endanswer, wr_answer)
                    else:
                        error_message = "End answer question structure doesn't conform to WR type question format."
                        add_error_message(question, error_message)
                        raise WREndStructureError(question.error)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

# ================================# ================================
#   Multi Select
# ================================# ================================


        elif question.questiontype == 'MS' or question.questiontype == 'MR':
            try:
                if question.questiontype == 'MR':
                    warning_message = 'Respondus format "Type: MR" was found on the file. Please use "Type: MS" instead.'
                    add_warning_message(question, warning_message)
                    raise RespondusTypeMRWarning(question.warning)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

            try:
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)
                    if question_type == 'inline_MS':
                        build_inline_MS(question, answers, is_random, enumeration)
                    else:
                        error_message = "Inline question structure doesn't conform to MS type question format."
                        add_error_message(question, error_message)
                        raise MSInlineStructureError(question.error)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)

                    if question_type == 'endanswer_MS':
                        build_endanswer_MS(question, answers, endanswer, is_random, enumeration)
                    else:
                        error_message = "End answer question structure doesn't conform to MS type question format."
                        add_error_message(question, error_message)
                        raise MSEndStructureError(question.error)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

# ================================# ================================
#   ORDERING
# ================================# ================================

        elif question.questiontype == 'ORD':
            try:
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)
                    if question_type == 'inline_ORD':
                        build_inline_ORD(question, answers)
                    else:
                        error_message = "Inline question structure doesn't conform to ORD type question format."
                        add_error_message(question, error_message)
                        raise ORDInlineStructureError(question.error)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)

                    if question_type == 'endanswer_ORD':
                        build_endanswer_ORD(question, endanswer)
                    else:
                        error_message = "End answer question structure doesn't conform to ORD type question format."
                        add_error_message(question, error_message)
                        raise ORDEndStructureError(question.error)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

# ================================# ================================
#   MULTIPLE CHOICE
# ================================# ================================

        elif question.questiontype == 'MC':
            try:
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)
                    if question_type == 'inline_MC':
                        build_inline_MC(question, answers, is_random, enumeration)
                    else:
                        error_message = "Inline question structure doesn't conform to MC type question format."
                        add_error_message(question, error_message)
                        raise MCInlineStructureError(question.error)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)

                    if question_type == 'endanswer_MC':
                        build_endanswer_MC(question, answers, endanswer, is_random, enumeration)
                    else:
                        error_message = "End answer question structure doesn't conform to MC type question format."
                        add_error_message(question, error_message)
                        raise MCEndStructureError(question.error)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

# ================================# ================================
#   TRUE-FALSE
# ================================# ================================

        elif question.questiontype == 'TF':
            try:
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)
                    if question_type == 'inline_TF':
                        build_inline_TF(question, answers, enumeration)
                    else:
                        error_message = "Inline question structure doesn't conform to TF type question format."
                        add_error_message(question, error_message)
                        raise TFInlineStructureError(question.error)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)

                    if question_type == 'endanswer_TF':
                        build_endanswer_TF(question, answers, endanswer, enumeration)
                    else:
                        error_message = "End answer question structure doesn't conform to TF type question format."
                        add_error_message(question, error_message)
                        raise TFEndStructureError(question.error)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

# ================================# ================================
#   FILL IN BLANK
# ================================# ================================

        elif question.questiontype == 'FIB' or question.questiontype == 'FMB':
            try:
                if question.questiontype == 'FMB':
                    warning_message = 'Respondus format "Type: FMB" was found on the file. Please use "Type: FIB" instead.'
                    add_warning_message(question, warning_message)
                    raise RespondusTypeFMBWarning(question.warning)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)
            try:
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)
                    if question_type == 'inline_FIB':
                        build_inline_FIB(question)
                    else:
                        error_message = "Inline question structure doesn't conform to FIB type question format."
                        add_error_message(question, error_message)
                        raise FIBInlineStructureError(question.error)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)

                    if question_type == 'endanswer_FIB':
                        build_endanswer_FIB(question, endanswer)
                    else:
                        error_message = "End answer question structure doesn't conform to FIB type question format."
                        add_error_message(question, error_message)
                        raise FIBEndStructureError(question.error)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

# ================================# ================================
#   MATCHING
# ================================# ================================

        elif question.questiontype == 'MAT' or question.questiontype == 'MT':
            try:
                if question.questiontype == 'MT':
                    warning_message = 'Respondus format "Type: MT" was found on the file. Please use "Type: MAT" instead.'
                    add_warning_message(question, warning_message)
                    raise RespondusTypeMTWarning(question.warning)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)
                
            try:
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)
                    if question_type == 'inline_MAT':
                        build_inline_MAT(question, answers)
                    else:
                        error_message = "Inline question structure doesn't conform to MAT type question format."
                        add_error_message(question, error_message)
                        raise MATInlineStructureError(question.error)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)

                    if question_type == 'endanswer_MAT':
                        build_endanswer_MAT(question, endanswer)
                    else:
                        error_message = "End answer question structure doesn't conform to MAT type question format."
                        add_error_message(question, error_message)
                        raise MATEndStructureError(question.error)
            except Exception as e:
                logger.error(e)
                # raise Exception(e)

# ================================# ================================
#   TYPE NOT GIVEN, TRY TO DETERMINE IT
# ================================# ================================

        else:
        # all other types try autodetect and compare if the given type is correct. if not then notify user.
            try:    
                if endanswer == None:
                    question_type = check_inline_questiontype(question, answers, wr_answer)
                else:
                    question_type = check_endanswer_questiontype(question, answers, endanswer)
                    
                # print("question_type:", question_type)
                match question_type:
                    case 'inline_MC':
                        build_inline_MC(question, answers, is_random, enumeration)
                    case 'endanswer_MC':
                        build_endanswer_MC(question, answers, endanswer, is_random, enumeration)
                    case 'inline_TF':
                        build_inline_TF(question, answers, enumeration)
                    case 'endanswer_TF':
                        build_endanswer_TF(question, answers, endanswer, enumeration)
                    case 'inline_MS':
                        build_inline_MS(question, answers, is_random, enumeration)
                    case 'endanswer_MS':
                        build_endanswer_MS(question, answers, endanswer, is_random, enumeration)
                    case 'inline_WR_keyword':
                        build_inline_WR_with_keyword(question, wr_answer)
                    case 'inline_WR_list':
                        build_inline_WR_with_list(question, answers)
                    case 'endanswer_WR':
                        build_endanswer_WR_with_list(question, endanswer, wr_answer)
                    case 'inline_FIB':
                        build_inline_FIB(question)
                    case 'endanswer_FIB':
                        build_endanswer_FIB(question, endanswer)
                    case 'inline_MAT':
                        build_inline_MAT(question, answers)
                    case 'endanswer_MAT':
                        build_endanswer_MAT(question, endanswer)
                    case 'inline_ORD':
                        build_inline_ORD(question, answers)
                    case 'endanswer_ORD':
                        build_endanswer_ORD(question, endanswer)
                    case 'inline_NO_TYPE':
                        error_message = "Cannot determined the inline question type."
                        add_error_message(question, error_message)
                        raise InlineNoTypeError(error_message)
                    case 'endanswer_NO_TYPE':
                        error_message = "Cannot determined the end answer question type."
                        add_error_message(question, error_message)
                        raise EndAnswerNoTypeError(error_message)
            except Exception as e:
                logger.error(e)
                raise NoTypeDeterminedError("Cannot determine the question type.")
    except Exception as e:
        logger.error(str(e))
        return "#" + str(question.number_provided) + " " + str(e)

    return "success"


@shared_task()
def run_pandoc_task(questionlibrary_id):
    questionlibrary = QuestionLibrary.objects.get(pk=questionlibrary_id)
    logger = FilenameLoggingAdapter(loggercelery, {
        'filename': questionlibrary.temp_file.name,
        'user_ip': questionlibrary.user_ip
        })
    try:
        import pypandoc
        mdblockquotePath = "./pandoc/pandoc-filters/mdblockquote.lua"
        emptyparaPath = "./pandoc/pandoc-filters/emptypara.lua"
        imageFilterPath = "./pandoc/pandoc-filters/image.lua"
        tables = "./pandoc/pandoc-filters/tables.lua"
        # listsPath = "./api/pandoc/pandoc-filters/lists.lua"

        pandoc_word_to_html = pypandoc.convert_file(
            questionlibrary.temp_file.path,
            format='docx+empty_paragraphs',
            to='html+empty_paragraphs+tex_math_single_backslash',
            extra_args=['--no-highlight',
            '--embed-resources',
            '--markdown-headings=atx',
            '--preserve-tabs',
            '--wrap=preserve',
            '--indent=false',
            '--mathml',
            '--ascii',
            # '--lua-filter=' + imageFilterPath
            ])
        pandoc_word_to_html = re.sub(r"(?!\s)<math>", " <math>", pandoc_word_to_html)
        pandoc_word_to_html = re.sub(r"</math>(?!\s)", "</math> ", pandoc_word_to_html)
        pandoc_html_to_md = pypandoc.convert_text(
            pandoc_word_to_html,
            'markdown_github+fancy_lists+emoji+hard_line_breaks+all_symbols_escapable+escaped_line_breaks+pipe_tables+startnum+tex_math_dollars',
            format='html+empty_paragraphs',
            extra_args=['--no-highlight', 
                        '--embed-resources',
                        '--markdown-headings=atx', 
                        '--preserve-tabs', 
                        '--wrap=preserve', 
                        '--indent=false', 
                        '--mathml', 
                        '--ascii',
                        '--lua-filter=' + mdblockquotePath, 
                        '--lua-filter=' + emptyparaPath,
                        # '--lua-filter=' + tables
                        ])
        pandoc_html_to_md = pandoc_html_to_md.rstrip()
        return "\n" + pandoc_html_to_md + "\n"
    except Exception as e:
        logger.debug(e)
        raise MarkDownConversionError(e)
