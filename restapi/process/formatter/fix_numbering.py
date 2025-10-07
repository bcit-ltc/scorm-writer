def fix_numbering(content_images_tagged, content_txt):
    import os
    import re
    import html
    import jaro 
    import logging
    logger = logging.getLogger(__name__)

    try:
        #remove empty lines
        ref_array = os.linesep.join([s for s in content_txt.splitlines() if s])

        # make array by splitting lines
        ref_array = ref_array.splitlines()
        pandoc_array = content_images_tagged.splitlines()

        ref_index = 0
        highest_score = 0
        for pandoc_index, pandoc_ref in enumerate(pandoc_array):
            # check if a list item
            number_pandoc = re.search(r"^ *([0-9]+)\\?[)|.]", pandoc_ref)
            if number_pandoc:   
                # unescape html characters like &rsquo; etc 
                pandoc_comp = html.unescape(pandoc_ref)
                # remove all non-letter characters
                pandoc_comp = re.findall(r'[a-zA-Z0-9]+', pandoc_comp)
                pandoc_comp = ''.join(pandoc_comp)
                for ref_index_it, ref_element in enumerate(ref_array[ref_index:len(ref_array)], start=ref_index):
                    # remove all non-letter/number characters
                    ref_comp = re.findall(r'[a-zA-Z0-9]+', ref_element)
                    ref_comp = ''.join(ref_comp)

                    number_ref = re.search(r"^ *([0-9]+)\\?[)|.]", ref_element)
                    number_ref_alt = re.search(r"^ *([0-9]+)", ref_element)

                    jaro_score = jaro.jaro_metric(ref_comp,pandoc_comp)
               
                    #check if reference is a number and skip if not a number
                    if not number_ref:
                        if number_ref_alt:
                            if jaro_score > 0.9:
                                error_question = number_pandoc.group(1)
                                if number_ref_alt:
                                    error_question = number_ref_alt.group(1)
                                raise QuestionEnumerationError(f'did not match the supported scorm-writer numberlist pattern "." or ") at question: {error_question}')
                        continue

                    ### FOR DEBUGGING specific line
                    # debug_line = '47'
                    # if number_pandoc.group(1) == debug_line:
                    #     logger.debug(f"ref_index = {ref_index} ref_index_it = {ref_index_it}")
                    #     logger.debug(f"ref_element =  {ref_element}")
                    #     logger.debug(f"ref: {ref_comp[0:120]}")
                    #     logger.debug(f"pandoc: {pandoc_comp[0:120]}")       
                    #     logger.debug(f"score: {jaro_score}")

                    if jaro_score > 0.9:
                        # matched by similarity
                        # if number_ref:
                        if number_ref.group(1) != number_pandoc.group(1):    
                            logger.debug(f"mismatch found [ref]:[pandoc]-[{number_ref.group(1)}:{number_pandoc.group(1)}]")
                            subbed = re.sub(r"[0-9]+", number_ref.group(1), pandoc_array[pandoc_index])
                            pandoc_array[pandoc_index] = subbed
                            logger.debug(f"mismatch fixed [ref]:[pandoc]-[{number_ref.group(1)}:{number_pandoc.group(1)}]->[{number_ref.group(1)}:{number_ref.group(1)}]")
                            ref_index = ref_index_it+1
                            break
                        else:
                            # number is the same and doesn't need fixing
                            ref_index = ref_index_it+1
                            break
                    else:
                        # no match; continue searching
                        if jaro_score > highest_score:
                            highest_score = jaro_score
                        # reached end of ref array without finding a match, comparison strings need to be checked or score needs to be adjusted
                        if ref_index_it == len(ref_array) - 1:
                            error_question = number_pandoc.group(1)
                            logger.warning(f'No reference line found with a high enough similarity score[{highest_score}] for question: {error_question}')
                            raise QuestionEnumerationError(f'No reference line found with a high enough similarity score[{highest_score}] for question: {error_question}')

        combined_string = '\n'.join(pandoc_array)
        return '\n' + combined_string
     
    except Exception as e:
        raise Exception(e)
    
class QuestionEnumerationError(Exception):
    def __init__(self, reason, message="QuestionEnumerationError"):
        self.reason = reason
        self.message = message
    def __str__(self):
        return f'{self.message} -> {self.reason}'