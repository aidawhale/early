"""
    Copyright 2020-2021 Paloma Piot Pérez-Abadín
	
	This file is part of early.
    early is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    early is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with early.  If not, see <https://www.gnu.org/licenses/>.
"""

from django.contrib.auth.models import User, Group
from django.db import models
from rest_framework import serializers
from app.api.models import Profile, ProfileData, Comment, Reason, GlobalData, Corpus
from django_countries.serializer_fields import CountryField

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'url', 'username', 'email', 'groups', 'first_name', 'last_name']


class UserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']

class ProfileDataSerializer(serializers.ModelSerializer):
    location = CountryField(required=False, allow_null=True)
    class Meta:
        model = ProfileData
        fields = ['id', 'age', 'gender', 'location', 'personality', 'depressed']

class ProfileDataExportSerializer(serializers.ModelSerializer):
    location = CountryField(required=False, allow_null=True)
    class Meta:
        model = ProfileData
        fields = ['age', 'gender', 'location', 'personality', 'depressed']

class ExportSerializer(serializers.ModelSerializer):
    validated_data = ProfileDataExportSerializer()
    class Meta:
        model = Profile        
        fields = ['id', 'experiment_id', 'validated_data']

class ReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reason
        fields = ['reason', 'profile_data_type']

class GlobalDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalData
        fields = ['id', 'load_in_progress', 'task_id']

class CorpusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Corpus
        fields = ['id', 'corpus_name']

class ProfileSerializer(serializers.ModelSerializer):
    system_data = ProfileDataSerializer(required=False, allow_null=True)
    validated_data = ProfileDataSerializer(required=False, allow_null=True)
    validated_by = UserNameSerializer(required=False, allow_null=True)
    reasons = ReasonSerializer(many=True, required=False, allow_null=True)

    # Create a custom method field
    data = serializers.SerializerMethodField('_datas')

    # Use this method for the custom field
    def _datas(self, obj):
        if (obj.validated_data is not None):
            return ProfileDataSerializer(obj.validated_data).data
        return ProfileDataSerializer(obj.system_data).data

    class Meta:
        model = Profile
        fields = ['id', 'experiment_id', 'reddit_username', 'corpus', 'is_valid', 'validated_by', 'system_data', 'validated_data', 'data', 'reasons', 'processed', 'questionnaire', 'questionnaire_reasons']
        read_only_fields = ['experiment_id', 'reddit_username', 'is_valid', 'validated_by', 'system_data', 'reasons']

    def update(self, instance, v_data):
        # update corpus
        corpus_data = v_data.pop('corpus', None)
        questionnaire_v_data = v_data.pop('questionnaire', None)
        questionnaire_reasons_v_data = v_data.pop('questionnaire_reasons', None)
        instance.corpus = corpus_data
        # questionnaire
        if questionnaire_v_data is not None:
            instance.questionnaire = questionnaire_v_data
        if questionnaire_reasons_v_data is not None:
            instance.questionnaire_reasons = questionnaire_reasons_v_data
        # validated data
        validated_data_v_data = v_data.pop('validated_data', None)
        if validated_data_v_data is not None:
            validated_data_serializer = self.fields['validated_data']
            if instance.validated_data is not None:
                instance.validated_data = validated_data_serializer.update(instance.validated_data, validated_data_v_data)
            else:
                instance.validated_data = validated_data_serializer.create(validated_data_v_data)
            instance.is_valid = True
            instance.processed = True
            instance.validated_by = self.context['request'].user
        # system data
        system_data_v_data = v_data.pop('system_data', None)
        if system_data_v_data is not None:
            system_data_serializer = self.fields['system_data']
            if instance.system_data is not None:
                instance.system_data = system_data_serializer.update(instance.system_data, system_data_v_data)
            else:
                instance.system_data = system_data_serializer.create(system_data_v_data)
        instance.save()
        return instance

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['date', 'text']

class CommentsCorpusSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, required=False)
    class Meta:
        model = Profile
        fields = ['id', 'corpus', 'comments']

class LabeledDataSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, required=False)
    validated_data = ProfileDataExportSerializer()
    class Meta:
        model = Profile
        fields = ['id', 'experiment_id', 'corpus', 'validated_data', 'comments']

class ProfileNLPSerializer(serializers.ModelSerializer):
    system_data = ProfileDataSerializer(required=False)
    validated_data = ProfileDataSerializer(read_only=True)
    reasons = ReasonSerializer(many=True, required=False)
    comments = CommentSerializer(many=True, required=False)

    class Meta:
        model = Profile        
        fields = ['id', 'experiment_id', 'reddit_username', 'corpus', 'system_data', 'validated_data', 'reasons', 'comments', 'questionnaire', 'questionnaire_reasons']
        read_only_fields = ['validated_data']

    def create(self, v_data):
        reasons_v_data = v_data.pop('reasons', [])
        comments_v_data = v_data.pop('comments', [])
        system_data_v_data = v_data.pop('system_data', None)
        questionnaire_v_data = v_data.pop('questionnaire', None)
        questionnaire_reasons_v_data = v_data.pop('questionnaire_reasons', None)

        try:
            instance = Profile.objects.get(reddit_username=v_data.get('reddit_username', None))
        except Profile.DoesNotExist:
            instance = Profile.objects.create(**v_data)
        system_data_serializer = self.fields['system_data']
        if system_data_v_data is not None:
            instance.system_data = system_data_serializer.create(system_data_v_data)
            instance.save()
        if questionnaire_v_data is not None:
            instance.questionnaire = questionnaire_v_data
            instance.save()
        if questionnaire_reasons_v_data is not None:
            instance.questionnaire_reasons = questionnaire_reasons_v_data
            instance.save()
        for reason in reasons_v_data:
            # if clasification score of same type -> update
            if "Classification score" in reason['reason']:
                Reason.objects.update_or_create(profile=instance, **reason)
            # if new reason -> only create if it's completely
            else:
                Reason.objects.get_or_create(profile=instance, **reason)
        last_date = None
        for comment in comments_v_data:
            c_date = None
            for key, value in comment.items():
                if key == 'date':
                    c_date = value
            # create comment if date doesnt exist
            if instance.last_retrieved_comment_date is None or instance.last_retrieved_comment_date < c_date:
                Comment.objects.create(profile=instance, **comment)
            if last_date is None or c_date > last_date:
                last_date = c_date

        instance.last_retrieved_comment_date = last_date
        return instance

