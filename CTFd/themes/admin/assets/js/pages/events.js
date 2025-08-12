import $ from "jquery";
import events from "../compat/events";
import CTFd from "../../lib/CTFd";

$(() => {
  events(CTFd.config.urlRoot);
});
