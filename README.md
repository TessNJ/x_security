# x

    {% if tweet.post_image_path: %}
    <img id="imagePreviewEdit" src="{{ url_for('static', filename='images/' ~ tweet.post_image_path) }}" alt="Post image" class="w-80">
    {% endif %}

    <input name="post_image_{{tweet.post_pk}}" id="post_image_{{tweet.post_pk}}" type="file" accept="image/*">
