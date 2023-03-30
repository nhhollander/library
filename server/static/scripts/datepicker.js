class DateTimePicker extends HTMLElement {

    static get observedAttributes() {
        return ['value', 'name', 'copy_from', 'copy_from_label'];
    }

    constructor() {
        super();
        this.attachShadow({mode: 'open'});

        const style = document.createElement("link");
        style.rel = "stylesheet";
        style.href = "/static/style.css";
        this.shadowRoot.append(style);

        const style2 = document.createElement("link");
        style2.rel = "stylesheet";
        style2.href = "/static/style/datepicker.css";
        this.shadowRoot.append(style2);

        // Build the nested form elements
        this.components = {};
        /* A container element shouldn't be required, but for some reason CSS applied to the `:root`
        tag within a shadow DOM are ignored. Not sure if this is a bug or intended behavior. */
        this.components.container = document.createElement("div");
        this.components.container.className = "container";
        this.components.picker = document.createElement("input");
        this.components.timezone = document.createElement("select");
        this.components.now_button = document.createElement("button");
        this.components.hidden_input = document.createElement("input");
        this.components.container.append(this.components.picker);
        this.components.container.append(this.components.timezone);
        this.components.container.append(this.components.now_button);
        this.shadowRoot.append(this.components.container);
        

        // Define the picker
        this.components.picker.type = "datetime-local";
        this.components.picker.step = "1";
        this.components.picker.addEventListener("change", this.update.bind(this));

        // Define the time zone selector
        this.components.timezone.addEventListener("change", this.update.bind(this));
        for(let i = -11.5; i <= 12; i+= 0.5) {
            /* Note: This function will generate some invalid timezone offsets but I don't care
            enough to exclude invalid ones. */
            const offset = i * 3600;  // seconds
            const hours = String(Math.abs(Math.trunc(i))).padStart(2, '0');
            const minutes = String(Math.abs((i % 1) * 60)).padStart(2, '0');
            const option = document.createElement("option");
            const sign = i >= 0 ? '+' : '-';
            option.innerText = `UTC${sign}${hours}:${minutes}`;
            option.value = `${sign}${hours}:${minutes}`;
            this.components.timezone.append(option);
        }

        // Define the "now" button
        this.components.now_button.innerText = "Now";
        this.components.now_button.type = "button";
        this.components.now_button.addEventListener("click", () => {
            const now = Temporal.Now.zonedDateTimeISO().round('second');
            this.components.picker.value = now.toString({offset:'never',timeZoneName:'never'});
            const offset = now.getISOFields()['offset'];
            for(const e of this.components.timezone.childNodes) {
                e.selected = e.value == offset;
            }
            this.update();
        });

        // Create a "hidden" input that will hold the value used when submitting forms
        this.components.hidden_input.type = "hidden";
    }

    /**
     * Perform initialization steps that require access to element attributes which are only
     * available at the time of insertion.
     */
    connectedCallback() {
        const initial_iso8601 = this.getAttribute('value') ||
            Temporal.Now.zonedDateTimeISO().round('second').toString({timeZoneName:'never'});
        this.set_value(initial_iso8601);

        this.components.hidden_input.name = this.getAttribute("name");
        this.append(this.components.hidden_input);

        const copy_from = this.getAttribute("copy_from");
        if(copy_from) {
            const copy_from_button = document.createElement("button");
            const label = this.getAttribute("copy_from_label") || copy_from;
            copy_from_button.innerText = `Copy from ${label}`;
            copy_from_button.addEventListener("click", () => {
                this.set_value(document.querySelector(`input[name="${copy_from}"]`).value);
            });
            this.components.container.append(copy_from_button);
        }
    }

    get value() {
        return this.components.hidden_input.value;
    }

    /**
     * Sets the value of the date picker.
     * 
     * The value must be an ISO8601 date string with 
     * @param {string} v 
     */
    set_value(v) {
        /* It is necessary to extract the offset from the input string and convert it into a
        pseudo-timezone name in order for Temporal to accept it. */
        const re = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([-+]\d{2}:\d{2}|Z)/;
        if(!re.test(v)) {
            throw new Error(`Input value ${v} is not a valid ISO8601 timestamp with timezone`);
        }
        const zone = v.match(re)[1];
        const tz_string = zone == 'Z' ? '+00:00' : zone;
        const zoned_datetime = Temporal.ZonedDateTime.from(`${v}[${tz_string}]`);

        this.setAttribute("value", v);
        this.components.hidden_input.value = v;

        this.components.picker.value = zoned_datetime.toString({offset:'never',timeZoneName:'never'});
        const offset = zoned_datetime.getISOFields()['offset'];
        for(const e of this.components.timezone.childNodes) {
            e.selected = e.value == offset;
        }
    }

    update() {
        const plain_dt = Temporal.PlainDateTime.from(this.components.picker.value);
        const time_zone = Temporal.TimeZone.from(
            this.components.timezone.options[this.components.timezone.selectedIndex].value);
        const zoned_dt = plain_dt.toZonedDateTime(time_zone);
        this.set_value(zoned_dt.toString({'timeZoneName':'never'}));
    }
}

customElements.define('date-time-picker', DateTimePicker);
