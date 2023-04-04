class TagPicker extends HTMLInputElement {

    tags = [];
    tag_names = [];
    selection_index = -1;
    max_selection_index = -1;
    previous_picker_value = null;

    constructor() {
        super();

        this.list_elem = document.createElement("div");
        this.list_elem.className = "tag-picker-list";
        this.hide_list();

        this.setAttribute("autocomplete", "off");

        this.addEventListener("keyup", this.update.bind(this));
        this.addEventListener("keydown", this.handle_arrow_keys.bind(this));
        this.addEventListener("keydown", this.handle_enter.bind(this));
        this.addEventListener("focusout", this.hide_list.bind(this));

        this.update_tag_list();
    }

    async update_tag_list() {
        const list = await fetch("/api/tags/list");
        const result = await list.json();
        if(result['result'] == "success") {
            this.tags = result['detail'];
            this.tag_names = this.tags.map((tag_object) => tag_object.name);
            console.log(this.tag_names);
            console.log(this.tags);
        } else {
            console.error("Failed to update tag list", result);
        }
    }

    connectedCallback() {
        this.after(this.list_elem);
    }

    hide_list() { this.list_elem.style.display = "none"; }
    show_list() { this.list_elem.style.display = "block"; }

    update() {
        if(this.previous_picker_value == this.value) {
            return;
        }

        this.previous_picker_value = this.value;
        this.selection_index = -1;
        this.max_selection_index = -1;

        const tokenized = new TokenizedString(this.value, this.selectionStart);
        const partial_tag = tokenized.active_token();

        this.list_elem.innerHTML = "";
        this.tags.forEach((tag) => {
            if(tag.name.includes(partial_tag) && !tokenized.tokens.includes(tag.name)) {
                const elem = document.createElement("div");
                elem.className = "tag";
                elem.setAttribute("tagName", tag.name);
                elem.addEventListener("mousedown", (e) => {
                    this.apply_suggestion(e.target.getAttribute("tagName"))
                });
                this.list_elem.append(elem);
                this.max_selection_index += 1;

                const name = document.createElement("span");
                name.className = "tag-name";
                name.innerText = tag.name;
                elem.appendChild(name);

                const count = document.createElement("span");
                count.className = "tag-count";
                count.innerText = tag.count;
                elem.appendChild(count);

            }
        })
        console.log(this.max_selection_index);
        this.max_selection_index >= 0 ? this.show_list() : this.hide_list();
    }

    apply_suggestion(tag) {
        const tokenized = new TokenizedString(this.value, this.selectionStart);
        tokenized.replace_active_token(tag);
        this.value = tokenized.toString();
    }

    handle_arrow_keys(event) {
        if(["ArrowDown", "ArrowUp"].includes(event.key)) event.preventDefault();

        if(event.key == "ArrowDown" && this.selection_index < this.max_selection_index) {
            this.selection_index += 1;
        } else if(event.key == "ArrowUp" && this.selection_index > 0) {
            this.selection_index -= 1;
        } else {
            return;
        }
        this.list_elem.querySelectorAll('.selected').forEach((e) => {
            e.classList.remove('selected');
        });
        const selected_element = this.list_elem.children[this.selection_index];
        selected_element.classList.add("selected");
        selected_element.scrollIntoView();
    }

    handle_enter(event) {
        if(event.key == "Enter" && this.selection_index >= 0) {
            this.apply_suggestion(
                this.list_elem.children[this.selection_index].getAttribute("tagName"));
            event.preventDefault();
        }
    }

}

class TokenizedString {

    constructor(string, cursor_character_index) {
        this.raw_string = string;
        this.tokens = string.split(' ');
        this.cursor_token_index = -1;
        let token_index = 0;
        this.tokens.forEach((token, index) => {
            token_index += token.length;
            if(cursor_character_index >= token_index && cursor_character_index <= token_index + token.length) {
                this.cursor_token_index = index;
            }
            token_index += 1;  // For the spaces between tokens
        });
    }

    active_token() {
        return this.tokens[this.cursor_token_index];
    }

    replace_active_token(new_value) {
        this.tokens[this.cursor_token_index] = new_value;
    }

    toString() {
        return this.tokens.join(' ');
    }

}

// On-load initializations
customElements.define('tag-picker2', TagPicker, {extends: 'input'});
const picker_style = document.createElement("link");
picker_style.rel = "stylesheet";
picker_style.href = "/static/style/tag-picker.css";
document.head.appendChild(picker_style);
