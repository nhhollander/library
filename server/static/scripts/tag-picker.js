class TagPicker extends HTMLElement {

    static get observedAttributes() {
        return ['value', 'name'];
    }

    constructor() {
        super();
        this.attachShadow({mode: 'open'});

        this.attachStyle("/static/style.css");
        this.attachStyle("/static/style/tag-picker.css");

        this.tags = [];
        this.selection_index = -1;
        this.max_selection_index = -1;
        this.previous_picker_value = null;

        this.components = {};
        this.components.picker = document.createElement("input");
        this.components.tag_list = document.createElement("div");
        this.components.hidden_input = document.createElement("input");
        this.shadowRoot.append(this.components.picker);
        this.shadowRoot.append(this.components.tag_list);

        this.components.picker.addEventListener("keyup", this.update.bind(this));
        this.components.picker.addEventListener("keydown", this.handle_arrow_keys.bind(this));
        this.components.picker.addEventListener("keydown", this.handle_enter.bind(this));
        this.components.picker.addEventListener("focusout", this.hide_list.bind(this));
        this.components.picker.addEventListener("change", this.update_value.bind(this));
        this.components.picker.setAttribute("list", "tag-picker-list");

        this.components.tag_list.className = "tag_list";
        this.components.tag_list.style.display = "none";

        this.update_tag_list();
    }

    connectedCallback() {
        this.components.hidden_input.name = this.getAttribute("name");
        this.components.hidden_input.value = this.getAttribute("value");
        this.append(this.components.hidden_input);
    }

    attachStyle(href) {
        const style = document.createElement("link");
        style.rel = "stylesheet";
        style.href = href;
        this.shadowRoot.append(style);
    }

    async update_tag_list() {
        const list = await fetch("/api/tags/list");
        const tag_result = await list.json();
        if(tag_result['result'] == "success") {
            this.tags = tag_result['detail'];
            console.log(this.tags);
        }
    }

    update() {
        if(this.components.picker.value == this.previous_picker_value) {
            return;
        }
        
        this.previous_picker_value = this.components.picker.value;
        this.selection_index = -1;
        this.max_selection_index = -1;

        const tokenized = new TokenizedString(this.components.picker.value, this.components.picker.selectionStart);
        const partial_tag = tokenized.active_token();

        this.components.tag_list.innerHTML = "";
        let index = 0;
        this.tags.forEach((tag) => {
            if(tag.name.includes(partial_tag) && !tokenized.tokens.includes(tag.name)) {
                const elem = document.createElement("div");
                elem.className = "tag-suggestion";
                elem.innerText = tag.name;
                elem.setAttribute("tagName", tag.name);
                elem.setAttribute("index", index);
                elem.addEventListener("mousedown", (e) => {
                    this.suggestion_selected(parseInt(e.target.getAttribute("index")))
                });
                this.components.tag_list.append(elem);
                this.max_selection_index += 1;
                index += 1;
            }
        });

        this.max_selection_index >= 0 ? this.show_list() : this.hide_list();
    }

    suggestion_selected(index) {
        if(index < 0 || index > this.components.max_selection_index) {
            console.warn(`Invalid suggestion selection index ${index}`);
            return;
        }
        console.log(this.components.tag_list.children, index);
        const tokenized = new TokenizedString(this.components.picker.value, this.components.picker.selectionStart);
        const new_value = this.components.tag_list.children[index].getAttribute("tagName");
        tokenized.replace_active_token(new_value);
        this.components.picker.value = tokenized.toString();
        this.components.hidden_input.value = tokenized.toString();
    }

    handle_arrow_keys(event) {
        // Up and down arrows normally move the cursor to the beginning/end (or up/down lines)
        if(["ArrowDown", "ArrowUp"].includes(event.key)) event.preventDefault();

        if(event.key == "ArrowDown" && this.selection_index < this.max_selection_index) {
            this.selection_index += 1;
        } else if(event.key == "ArrowUp" && this.selection_index > 0) {
            this.selection_index -= 1;
        } else {
            return;
        }
        this.components.tag_list.querySelectorAll('.selected').forEach((e) => {
            e.classList.remove('selected');
        })
        this.components.tag_list.children[this.selection_index].classList.add("selected");
    }

    handle_enter(event) {
        if(event.key == "Enter") {
            this.suggestion_selected(this.selection_index);
        }
    }

    update_value() {
        this.components.hidden_input.value = this.components.picker.value;
    }

    hide_list() {
        this.components.tag_list.style.display = "none";
    }

    show_list() {
        this.components.tag_list.style.display = "block";
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

customElements.define('tag-picker', TagPicker);
