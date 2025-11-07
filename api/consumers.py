import json
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.files.base import ContentFile
import base64
from os.path import normpath
from .models import Question, Section, QuestionLibrary, \
    Image, MultipleChoice, MultipleChoiceAnswer, TrueFalse, Fib, MultipleSelect, MultipleSelectAnswer, \
        Matching, MatchingAnswer, MatchingChoice, Ordering, WrittenResponse
import re
import logging
newlogger = logging.getLogger(__name__)
from .logging.logging_adapter import FilenameLoggingAdapter
# from .logging.contextfilter import QuestionlibraryFilenameFilter
# logger.addFilter(QuestionlibraryFilenameFilter())
from .logging.ErrorTypes import EMFImageError
from .process.process_helper import add_error_message, html_to_plain, trim_text
from .serializers import JsonResponseSerializer
from .process.process import Process

from .process.extract_images import ImageExtractError
from .process.formatter import FormatterError
from .process.sectioner import SectionerError
from .process.splitter import SplitterError
from .process.endanswers import EndAnswerError
from .process.parser import ParserError
from .tasks import MarkDownConversionError

# class FilenameLoggingAdapter(logging.LoggerAdapter):
#     """
#     This example adapter expects the passed in dict-like object to have a
#     'connid' key, whose value in brackets is prepended to the log message.
#     """
#     def process(self, msg, kwargs):
#         return f"[{self.extra['filename']}] {msg}", kwargs

class TextConsumer(JsonWebsocketConsumer):

    def connect(self):
        newlogger.info("New connection started")
        sessionid = None
        # print(self.scope['url_route']['kwargs']['session_id'])
        # self.sessionid = self.scope['url_route']['kwargs']['session_id']
        # self.channel_layer.group_add(self.sessionid, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        self.close()
        newlogger.info("Closing Connection")
        # self.channel_layer.group_discard(self.sessionid, self.channel_name)

    # Replace image marker  with actual img element and return a boolean
    def replace_image(self, obj, key, process, logger):
        regex = r"(?<=&lt;&lt;&lt;&lt;)\d+(?=&gt;&gt;&gt;&gt;)"
        obj_text = getattr(obj, key)
        is_image = None
        if obj_text:
            is_image = re.search(regex, obj_text)
        
        if is_image != None:
            obj_name = obj._meta.model.__name__
            if obj_name == "Question":
                logger.debug(f'Adding Image(s) to Question #{obj.number_provided}')
            elif obj_name == "Section":
                logger.debug(f'Adding Image(s) to Section "{obj.title}"')
            else:
                logger.debug(f'Adding Image(s) to a {obj_name}')
                
            image_ids = list(set(re.findall(regex, obj_text)))
            for image_id in image_ids:
                image = process.questionlibrary.get_image(int(image_id))
                img_src = image.image
                placeholder = "&lt;&lt;&lt;&lt;" + image_id + "&gt;&gt;&gt;&gt;"

                if re.match(r"\<img\s+src\=\"data\:image\/x\-emf\;", img_src):
                    try:
                        error_message = "EMF image format is NOT supported. Please replace this image with JPG or PNG format."
                        img_src = f'<img src="media/broken-image.emf" alt="BROKEN IMAGE" style="color:red; font-size:2em;">'
                        add_error_message(obj, error_message)
                        raise EMFImageError(obj.error)
                    except Exception as e:
                        logger.error(e)

                obj_text = re.sub(placeholder, lambda x: image.image, obj_text)

            setattr(obj, key, obj_text)
            obj.save()
            return True
        return False



    def receive_json(self, content, **kwargs):
###########################################
        # Save the file
###########################################
        try:
            newlogger.info("Process Start")
            format, fixeddata = content.get('file').split(';base64,')
            received_file = ContentFile(base64.b64decode(fixeddata),
                                        name=content.get('filename'))

            new_questionlibrary = QuestionLibrary.objects.create()

            new_questionlibrary.temp_file = received_file
            # new_questionlibrary.session_id = self.sessionid
            new_questionlibrary.main_title = content.get('filename').split(".")[0]
            new_questionlibrary.randomize_answer = content.get('randomize_answer')
            media_folder = content.get('media_folder')
            if media_folder != None:
                media_folder = normpath(media_folder).lstrip('/')
                new_questionlibrary.media_folder = media_folder
            enumeration = content.get('enumeration')
            if enumeration and enumeration > 0 and enumeration < 7:
                new_questionlibrary.enumeration = enumeration

            new_questionlibrary.user_ip = content.get('user_ip')
            new_questionlibrary.save()
            process = Process(new_questionlibrary)
            logger = FilenameLoggingAdapter(newlogger, {
                'filename': new_questionlibrary.temp_file.name,
                'user_ip': new_questionlibrary.user_ip
                })
            logger.info("File Saved")
        except Exception as e:
            logger.error("Not a valid .docx File: {e}")
            self.send(text_data=json.dumps(process.sendformat("Error", "Not a valid .docx File", "")))
            # close connection
            self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
            return
        
###########################################
        # create_pandocstring
###########################################

        try:
            # process.questionlibrary.create_pandocstring()
            process.run_pandoc()
            logger.info("Pandoc DONE")
        except Exception as e:
            logger.error(str(e))
            self.send(
                text_data=json.dumps(process.sendformat("Error", "File unreadable", "")))
            # close connection
            self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
            # return
        # except Exception as e:
        #     self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
        #     logger.error(str(e))
        #     return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "The file is valid", "")))

###########################################
        # Extract Images
###########################################

        try:
            process.extract_images()
            logger.info("Done extracting Images")
        except ImageExtractError as e:
            self.send(text_data=json.dumps(process.sendformat("Warn", "Images extraction failed", "")))
        else:
            logger.info(f'{str(process.images_extracted)} Images Extracted')
            self.send(text_data=json.dumps(process.sendformat("Busy", "Image found: " + str(process.images_extracted), "")))

###########################################
        # Convert to txt for fixing numbering
###########################################

        try:
            process.convert_txt()
            logger.info("convert txt DONE")
        except Exception as e:
            logger.error(e)

###########################################
        # Fix Numbering (broken lists)
###########################################

        try:
            process.fix_numbering()
            logger.info("numbering fix DONE")
        except Exception as e:
            logger.error(e)
            self.send(
                text_data=json.dumps(process.sendformat("Error", str(e), "")))
            # close connection
            # self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
            return

##########################################
        # run_formatter
##########################################
        logger.debug("Formatting ...")
        try:
            process.run_formatter()
            logger.info("Formatter DONE")
        except FormatterError as e:
            logger.error("FormatterError: " + str(e))
            self.send(text_data=json.dumps(process.sendformat("Error", "No contents found in the body of the file", "")))
            # close connection
            self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
            return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Content Body detected", "")))

##########################################
        # run_sectioner
##########################################
        logger.debug("Sectioning ...")
        try:
            process.run_sectioner()
            logger.info("Sectioner DONE")
        except SectionerError as e:
            logger.error("SectionerError: " + str(e))
            self.send(text_data=json.dumps(process.sendformat("Error", "Sections can not be identified", "")))
            # close connection
            self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
            return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Section found: " + str(process.subsection_count), "")))

##########################################
        # run_splitter
##########################################
        logger.debug("Splitting Questions ...")
        try:
            process.run_splitter()
            logger.info("Splitter DONE")
        except Exception as e:
            logger.error("SplitterError: " + str(e))
            self.send(text_data=json.dumps(process.sendformat("Error", "Splitter failed", "")))
            # close connection
            self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
            return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Question found: " + str(process.questions_expected), "")))
###########################################
        # Grab end answers
###########################################
        logger.debug("Checking Endanswer ...")
        try:
            process.get_endanswers()
            logger.info("Check Endanswer DONE")
        except EndAnswerError as e:
            logger.error("EndAnswerError: " + str(e))
            self.send(text_data=json.dumps(process.sendformat("Busy", "Endanswers not found", "")))
        else:
            if process.endanswers_count > 0:
                self.send(text_data=json.dumps(process.sendformat("Busy", "End answers found", "")))

###########################################
        # run_parser
###########################################
        logger.debug("Starting Parser ...")
        try:
            process.run_parser()
            logger.info("Parser DONE")
        except Exception as e:
            logger.error("ParserError: " + str(e))
            self.send(text_data=json.dumps(process.sendformat("Error", "Parser failed", "")))
                # close connection
            self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Parser complete", "")))

###########################################
        # Loop All Sections and Questions to count error, add/replace images, and add question.title 
###########################################
        logger.debug("Start Adding Images back ...")
        try:
            # select all sections for this QL
            sections = process.questionlibrary.get_sections()
            for section in sections:
                
                # DO NOT DELETE: replace images in section.text
                section_replace_image = self.replace_image(section, "text", process, logger)

                # select all questions for this QL
                questions = Question.objects.filter(section=section)

                for question in questions:
                    is_table = False
                    img_replaced = False

###########################################
    # count all question level errors
###########################################
                    # logger.debug("count all question level errors ...")
                    if question.info is not None:
                        process.question_info_count += 1

                    if question.warning is not None:
                        process.question_warning_count += 1

                    if question.error is not None:
                        process.question_error_count += 1


                    is_table = re.search(r"<table(.|\n)+?</table>", question.text) or is_table

###########################################
    # replace Image placeholder for questions
###########################################

                    # replace image in question.text if exist
                    img_replaced = self.replace_image(question, 'text', process, logger) or img_replaced

                    match(question.questiontype):
                        case 'MC':
                            #Check MC
                            MC_answer_objects = MultipleChoiceAnswer.objects.filter(multiple_choice__question=question)
                            for answer in MC_answer_objects:
                                img_replaced = self.replace_image(answer, 'answer', process, logger) or img_replaced
                                is_table = re.search(r"<table(.|\n)+?</table>", answer.answer) or is_table
                                if answer.answer_feedback is not None:
                                    img_replaced = self.replace_image(answer, 'answer_feedback', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", answer.answer_feedback) or is_table
                        case 'TF':
                            #Check TF
                            TF_object = TrueFalse.objects.filter(question=question)
                            for tf in TF_object:
                                if tf.true_feedback is not None:
                                    img_replaced = self.replace_image(tf, 'true_feedback', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", tf.true_feedback) or is_table
                                if tf.false_feedback is not None:
                                    img_replaced = self.replace_image(tf, 'false_feedback', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", tf.false_feedback) or is_table
                        case 'FIB' | 'FMB':
                            #Check FIB
                            FIB_object = Fib.objects.filter(question=question)
                            for fib_question in FIB_object:
                                img_replaced = self.replace_image(fib_question, 'text', process, logger) or img_replaced
                                is_table = re.search(r"<table(.|\n)+?</table>", fib_question.text) or is_table
                        case 'MS' | 'MR':
                            #Check MS
                            MS_answer_objects = MultipleSelectAnswer.objects.filter(multiple_select__question=question)
                            for answer in MS_answer_objects:
                                img_replaced = self.replace_image(answer, 'answer', process, logger) or img_replaced
                                is_table = re.search(r"<table(.|\n)+?</table>", answer.answer) or is_table
                                if answer.answer_feedback is not None:
                                    img_replaced = self.replace_image(answer, 'answer_feedback', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", answer.answer_feedback) or is_table
                        case 'ORD':
                            #Check ORD
                            ORD_objects = Ordering.objects.filter(question=question)
                            for ordering in ORD_objects:
                                if ordering.text is not None:
                                    img_replaced = self.replace_image(ordering, 'text', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", ordering.text) or is_table
                                if ordering.ord_feedback is not None:
                                    img_replaced = self.replace_image(ordering, 'ord_feedback', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", ordering.ord_feedback) or is_table
                        case 'MAT' | 'MT':
                            #Check MAT answer
                            MAT_answer_objects = MatchingAnswer.objects.filter(matching_choice__matching__question=question)
                            for mat_answer in MAT_answer_objects:
                                if mat_answer.answer_text is not None:
                                    img_replaced = self.replace_image(mat_answer, 'answer_text', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", mat_answer.answer_text) or is_table
                            #Check MAT choice
                            MAT_choice_objects = MatchingChoice.objects.filter(matching__question=question)
                            for mat_choice in MAT_choice_objects:
                                if mat_choice.choice_text is not None:
                                    img_replaced = self.replace_image(mat_choice, 'choice_text', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", mat_choice.choice_text) or is_table
                        case 'WR' | 'E':
                            #Check WR
                            WR_objects = WrittenResponse.objects.filter(question=question)
                            for wr in WR_objects:
                                if wr.initial_text is not None:
                                    img_replaced = self.replace_image(wr, 'initial_text', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", wr.initial_text) or is_table
                                if wr.answer_key is not None:
                                    img_replaced = self.replace_image(wr, 'answer_key', process, logger) or img_replaced
                                    is_table = re.search(r"<table(.|\n)+?</table>", wr.answer_key) or is_table


###########################################
    # Add question.title
###########################################                   
                    prefix = ''

                    if is_table:
                        prefix = '[TABLE]' + prefix
                    if img_replaced:
                        prefix = '[IMG]' + prefix
                    
                    # Save question.title
                    if question.title is None:
                        title_text = question.text
                        title_text = title_text.replace('\n', ' ')
                        title_text = re.sub(r"<img\s+(.)+?\s+\/>", "[IMG]", title_text)
                        title_text = re.sub(r"<table(.|\n)+?</table>", "[TABLE]", title_text)
                        title_text = re.sub(r"&lt;&lt;&lt;&lt;\d+&gt;&gt;&gt;&gt;", "[IMG]", title_text)
                        
                        if question.questiontype == 'FIB' or question.questiontype == 'FMB':
                            title_text = re.sub(r"\[(.*?)\]", "_______", title_text)

                        title_text = html_to_plain(title_text)
                        title_text = trim_text(title_text)
                        
                        if prefix != '':
                            prefix = prefix + ' '
                            title_text = re.sub(r"\s*\[IMG\]", "", title_text).strip()
                            title_text = re.sub(r"\s*\[TABLE\]", "", title_text).strip()
                            
                        title_text = prefix + title_text
                        question.title = title_text[0:127]
                        question.save()
                        
        except Exception as e:
            logger.error(e)

        logger.debug("Adding Images back DONE")



###########################################
        # serialize and send response
###########################################
        logger.info("Process End")

        serialized_ql = JsonResponseSerializer(process.questionlibrary)
        self.send(text_data=json.dumps(process.sendformat("Done", "", serialized_ql.data)))

######################### Close Connection
        self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
        self.close()
