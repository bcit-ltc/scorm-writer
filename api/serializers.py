# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers
from .models import Matching, MatchingAnswer, MatchingChoice, Ordering, QuestionLibrary, Section, Question, MultipleChoice, MultipleChoiceAnswer, TrueFalse, Fib, MultipleSelect, MultipleSelectAnswer, WrittenResponse
from django.conf import settings

class JsonToScormSerializer(serializers.Serializer):
    json_data = serializers.JSONField(initial=dict)

    def create(self, validated_data):
        newconversion = QuestionLibrary.objects.create()
        newconversion.json_data = validated_data.get('json_data', validated_data)

        newconversion.folder_path = settings.MEDIA_ROOT + str(newconversion.id)
        newconversion.image_path = newconversion.folder_path + settings.MEDIA_URL
        newconversion.create_directory()
        newconversion.save()

        import logging
        logger = logging.getLogger(__name__)

        logger.info("[" + str(newconversion.id) + "] " + "<<<<<<<<<<Transaction Started<<<<<<<<<<")
        # ===========  1  ==================
        # newconversion.create_pandocstring()
        # ===========  2  ==================
        # newconversion.run_parser()

        # count_errors(newconversion)

        # if newconversion.total_document_errors == 0:
        #     # ===========  3, 4, 5  ==================
        # print("newconversion.create_xml_files()--------------------------------------")
        # newconversion.create_xml_files()
        # print("newconversion.zip_files()--------------------------------------")
        #     # ===========  6  ==================
        # newconversion.zip_files()

        return newconversion

    # def update(self, instance, validated_data):
    #     instance.temp_file = validated_data.get('temp_file',
    #                                             instance.temp_file)
    #     instance.save()
    #     return instance


class MultipleChoiceAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = MultipleChoiceAnswer
        fields = ['index', 'order', 'answer', 'answer_feedback', 'weight']


class MultipleChoiceSerializer(serializers.ModelSerializer):
    multiple_choice_answers = serializers.SerializerMethodField()

    def get_multiple_choice_answers(self, multiple_choice):
        multiple_choice_answer_queryset = multiple_choice.get_multiple_choice_answers()
        serializer = MultipleChoiceAnswerSerializer(instance=multiple_choice_answer_queryset, many=True, allow_null=True)
        return serializer.data

    class Meta:
        model = MultipleChoice
        fields = ['randomize', 'enumeration', 'multiple_choice_answers']


class TrueFalseSerializer(serializers.ModelSerializer):

    class Meta:
        model = TrueFalse
        fields = ['true_weight', 'true_feedback', 'false_weight', 'false_feedback', 'enumeration']


class FibSerializer(serializers.ModelSerializer):

    class Meta:
        model = Fib
        fields = ['type', 'text', 'order', 'size', 'weight']


class OrderingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ordering
        fields = ['text', 'order', 'ord_feedback']


class MultipleSelectAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = MultipleSelectAnswer
        fields = ['index', 'order', 'answer', 'answer_feedback', 'is_correct']


class MultipleSelectSerializer(serializers.ModelSerializer):
    multiple_select_answers = serializers.SerializerMethodField()

    def get_multiple_select_answers(self, multiple_select):
        multiple_select_answer_queryset = multiple_select.get_multiple_select_answers()
        serializer = MultipleSelectAnswerSerializer(instance=multiple_select_answer_queryset, many=True, allow_null=True)
        return serializer.data

    class Meta:
        model = MultipleSelect
        fields = ['randomize', 'enumeration', 'style', 'grading_type', 'multiple_select_answers']


class MatchingAnswersSerializer(serializers.ModelSerializer):

    class Meta:
        model = MatchingAnswer
        fields = ['answer_text']


class MatchingChoiceSerializer(serializers.ModelSerializer):
    matching_answers = MatchingAnswersSerializer(many=True, allow_null=True)

    class Meta:
        model = MatchingChoice
        fields = ['choice_text', 'matching_answers']


class MatchingSerializer(serializers.ModelSerializer):
    matching_choices = MatchingChoiceSerializer(many=True, allow_null=True)

    class Meta:
        model = Matching
        fields = ['grading_type', 'matching_choices']


class WrittenResponseSerializer(serializers.ModelSerializer):

    class Meta:
        model = WrittenResponse
        fields = ['enable_student_editor', 'initial_text', 'answer_key', 'enable_attachments']


class QuestionSerializer(serializers.ModelSerializer):
    multiple_choice = MultipleChoiceSerializer(many=True, allow_null=True)
    true_false = TrueFalseSerializer(many=True, allow_null=True)
    fib = serializers.SerializerMethodField()
    multiple_select = MultipleSelectSerializer(many=True, allow_null=True)
    matching = MatchingSerializer(many=True, allow_null=True)
    ordering = serializers.SerializerMethodField()
    written_response = WrittenResponseSerializer(many=True, allow_null=True)

    def get_fib(self, question):
        ordering_queryset = question.get_fibs()
        serializer = FibSerializer(instance=ordering_queryset, many=True, allow_null=True)
        return serializer.data
    
    def get_ordering(self, question):
        ordering_queryset = question.get_orderings()
        serializer = OrderingSerializer(instance=ordering_queryset, many=True, allow_null=True)
        return serializer.data

    class Meta:
        model = Question
        fields = ['index', 'title', 'questiontype', 'text', 'points', 'difficulty', 'mandatory', 'hint', 'feedback', 'multiple_choice', 'true_false', 'fib', 'multiple_select', 'matching', 'ordering', 'written_response', 'raw_header', 'number_provided', 'raw_content', 'warning', 'error']


class SectionSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    def get_questions(self, section):
        question_queryset = section.get_questions()
        serializer = QuestionSerializer(instance=question_queryset, many=True)
        return serializer.data
    class Meta:
        model = Section
        fields = ['is_main_content', 'order', 'title', 'is_title_displayed', 'text', 'is_text_displayed', 'shuffle', 'questions', 'error']


class JsonResponseSerializer(serializers.ModelSerializer):
    # sections = SectionSerializer(many=True, read_only=True)
    sections = serializers.SerializerMethodField()

    def get_sections(self, questionlibrary):
        section_queryset = questionlibrary.get_sections()
        serializer = SectionSerializer(instance=section_queryset, many=True)
        return serializer.data
    class Meta:
        model = QuestionLibrary
        fields = ['main_title', 'randomize_answer', 'enumeration', 'media_folder', 'sections']


##############################   `/package` serializers   ##############################

class MultipleChoicePackageSerializer(serializers.ModelSerializer):
    multiple_choice_answers = MultipleChoiceAnswerSerializer(many=True, allow_null=True)

    class Meta:
        model = MultipleChoice
        fields = ['randomize', 'enumeration', 'multiple_choice_answers']


class MultipleSelectPackageSerializer(serializers.ModelSerializer):
    multiple_select_answers = MultipleSelectAnswerSerializer(many=True, allow_null=True)

    class Meta:
        model = MultipleSelect
        fields = ['randomize', 'enumeration', 'style', 'grading_type', 'multiple_select_answers']


class QuestionPackageSerializer(serializers.ModelSerializer):
    multiple_choice = MultipleChoicePackageSerializer(many=True, allow_null=True)
    true_false = TrueFalseSerializer(many=True, allow_null=True)
    fib = FibSerializer(many=True, allow_null=True)
    multiple_select = MultipleSelectPackageSerializer(many=True, allow_null=True)
    matching = MatchingSerializer(many=True, allow_null=True)
    ordering = OrderingSerializer(many=True, allow_null=True)
    written_response = WrittenResponseSerializer(many=True, allow_null=True)

    class Meta:
        model = Question
        fields = ['index', 'title', 'questiontype', 'text', 'points', 'difficulty', 'mandatory', 'hint', 'feedback', 'multiple_choice', 'true_false', 'fib', 'multiple_select', 'matching', 'ordering', 'written_response', 'raw_header', 'number_provided', 'raw_content', 'warning', 'error']


class SectionPackageSerializer(serializers.ModelSerializer):
    questions = QuestionPackageSerializer(many=True, allow_null=True)
    
    class Meta:
        model = Section
        fields = ['is_main_content', 'order', 'title', 'is_title_displayed', 'text', 'is_text_displayed', 'shuffle', 'questions', 'error']


class QuestionLibraryPackageSerializer(serializers.ModelSerializer):
    sections = SectionPackageSerializer(many=True, allow_null=True)

    class Meta:
        model = QuestionLibrary
        fields = ['main_title', 'randomize_answer', 'enumeration', 'media_folder', 'formatter_output', 'sectioner_output', 'sections']

    def create(self, validated_data):
        sections_data = validated_data.pop('sections')
        question_library_instance = QuestionLibrary.objects.create(**validated_data)

        for section in sections_data:
            questions_data = section.pop('questions')
            section_instance = Section.objects.create(question_library=question_library_instance, **section)

            for question in questions_data:
                mc_data = question.pop('multiple_choice')
                tf_data = question.pop('true_false')
                fib_data = question.pop('fib')
                ms_data = question.pop('multiple_select')
                mat_data = question.pop('matching')
                ord_data = question.pop('ordering')
                wr_data = question.pop('written_response')
                question_instance = Question.objects.create(section=section_instance, **question)

                if mc_data:
                    for multiple_choice in mc_data:
                        mc_answers_data = multiple_choice.pop('multiple_choice_answers')
                        mc_instance = MultipleChoice.objects.create(question=question_instance, **multiple_choice)

                        for mc_answers in mc_answers_data:
                            mc_answers_instance = MultipleChoiceAnswer.objects.create(multiple_choice=mc_instance, **mc_answers)

                if tf_data:
                    for true_false in tf_data:
                        tf_instance = TrueFalse.objects.create(question=question_instance, **true_false)

                if fib_data:
                    for fib_item in fib_data:
                        fib_item_instance = Fib.objects.create(question=question_instance, **fib_item)

                if ms_data:
                    for multiple_select in ms_data:
                        ms_answers_data = multiple_select.pop('multiple_select_answers')
                        ms_instance = MultipleSelect.objects.create(question=question_instance, **multiple_select)

                        for ms_answers in ms_answers_data:
                            ms_answers_instance = MultipleSelectAnswer.objects.create(multiple_select=ms_instance, **ms_answers)

                if mat_data:
                    for matching in mat_data:
                        mat_choices_data = matching.pop('matching_choices')

                        matching_instance = Matching.objects.create(question=question_instance, **matching)

                        for mat_choice_item in mat_choices_data:
                            mat_answers_data = mat_choice_item.pop('matching_answers')
                            mat_choice_item_instance = MatchingChoice.objects.create(matching=matching_instance, **mat_choice_item)

                            for mat_answer_item in mat_answers_data:
                                mat_answer_item_instance = MatchingAnswer.objects.create(matching_choice=mat_choice_item_instance, **mat_answer_item)

                if ord_data:
                    for ord_item in ord_data:
                        ord_item_instance = Ordering.objects.create(question=question_instance, **ord_item)

                if wr_data:
                    for written_response in wr_data:
                        wr_instance = WrittenResponse.objects.create(question=question_instance, **written_response)

        return question_library_instance

class StatusResponseSerializer(serializers.Serializer):
    version_number = serializers.CharField(max_length=None, min_length=None, allow_blank=True, trim_whitespace=True)
