# Comments
{% for comment in comments|reverse %}
# {{loop.index}}
**Author:**  {{ comment.user.firstName }} {{ comment.user.lastName }} ({{ comment.user.username }})  
**Time:** {{ comment.creationTime }}  
{{ comment.comment }}
{% if comment.attachment is defined %}   
## Attachments
[{{ comment.attachment.name }}](comments/{{ comment.attachment.id }}_{{ comment.attachment.name }})
{% endif %}  
{% endfor %}