# {{ challange.title }}
**Event:** {{ event.name }}  
**Date:** {{ event.startTime }} - {{ event.endTime }}  
**Participant Count:** {{ event.participantCount }}

<hr/>

{% for section in challange.sections %}  
{{section.content}}  
{% for step in section.steps %} 
## Step {{loop.index}}  
{{ step.content }}  
{% endfor %}  
{% endfor %}  
