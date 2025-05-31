import Alpine from "alpinejs";
import CTFd from "../index";
import { serializeJSON } from "@ctfdio/ctfd-js/forms";
import { copyToClipboard } from "../utils/clipboard";
import { colorHash } from "@ctfdio/ctfd-js/ui";
import { getOption as getUserScoreOption } from "../utils/graphs/echarts/userscore";
import { embed } from "../utils/graphs/echarts";

window.Alpine = Alpine;
window.CTFd = CTFd;

Alpine.store('modals', {
  teamEditModal: null,
  teamCaptainModal: null,
  teamInviteModal: null,
  teamDisbandModal: null,
  teamEditModalInitialized: false,
  teamCaptainModalInitialized: false,
  teamInviteModalInitialized: false,
  teamDisbandModalInitialized: false,
});

Alpine.data("TeamEditModal", () => ({
  success: null,
  error: null,
  initial: null,
  errors: [],

  init() {
    this.initial = serializeJSON(this.$el.querySelector("form"));
    if (!Alpine.store('modals').teamEditModalInitialized) {
      Alpine.store('modals').teamEditModal = this.$refs.teamEditModal;
      Alpine.store('modals').teamEditModalInitialized = true;
    }
  },

  async updateProfile() {
    let data = serializeJSON(this.$el, this.initial, true);

    data.fields = [];

    for (const property in data) {
      if (property.match(/fields\[\d+\]/)) {
        let field = {};
        let id = parseInt(property.slice(7, -1));
        field["field_id"] = id;
        field["value"] = data[property];
        data.fields.push(field);
        delete data[property];
      }
    }

    let response = await CTFd.pages.teams.updateTeamSettings(data);
    if (response.success) {
      this.success = true;
      this.error = false;
      setTimeout(() => {
        this.success = null;
        this.error = null;
      }, 3000);
      this.isOpen = false;
    } else {
      this.success = false;
      this.error = true;
      Object.keys(response.errors).map(error => {
        const error_msg = response.errors[error];
        this.errors.push(error_msg);
      });
    }
  },

  openModal() {
    if (this.$refs.teamEditModal) {
      this.$refs.teamEditModal.style.display = 'block';
    }
  },

  closeModal() {
    if (this.$refs.teamEditModal) {
      this.$refs.teamEditModal.style.display = 'none';
    }
  },
}));

Alpine.data("TeamCaptainModal", () => ({
  success: null,
  error: null,
  errors: [],

  init() {
    Alpine.store('modals').teamCaptainModal = this.$refs.teamCaptainModal;
    if (!Alpine.store('modals').teamCaptainModalInitialized) {
      Alpine.store('modals').teamCaptainModal = this.$refs.teamCaptainModal;
      Alpine.store('modals').teamCaptainModalInitialized = true;
    }
  },

  async updateCaptain() {
    let data = serializeJSON(this.$el, null, true);
    let response = await CTFd.pages.teams.updateTeamSettings(data);

    if (response.success) {
      window.location.reload();
    } else {
      this.success = false;
      this.error = true;
      Object.keys(response.errors).map(error => {
        const error_msg = response.errors[error];
        this.errors.push(error_msg);
      });
    }
  },

  openModal() {
    if (this.$refs.teamCaptainModal) {
      this.$refs.teamCaptainModal.style.display = 'block';
    }
  },

  closeModal() {
    if (this.$refs.teamCaptainModal) {
      this.$refs.teamCaptainModal.style.display = 'none';
    }
  },
}));

Alpine.data("TeamInviteModal", () => ({
  init() {
    Alpine.store('modals').teamInviteModal = this.$refs.teamInviteModal;
    if (!Alpine.store('modals').teamInviteModalInitialized) {
      Alpine.store('modals').teamInviteModal = this.$refs.teamInviteModal;
      Alpine.store('modals').teamInviteModalInitialized = true;
    }
  },

  copy() {
    copyToClipboard(this.$refs.link);
  },

  openModal() {
    if (this.$refs.teamInviteModal) {
      this.$refs.teamInviteModal.style.display = 'block';
    }
  },

  closeModal() {
    if (this.$refs.teamInviteModal) {
      this.$refs.teamInviteModal.style.display = 'none';
    }
  },
}));

Alpine.data("TeamDisbandModal", () => ({
  errors: [],

  init() {
    Alpine.store('modals').teamDisbandModal = this.$refs.teamDisbandModal;
    if (!Alpine.store('modals').teamDisbandModalInitialized) {
      Alpine.store('modals').teamDisbandModal = this.$refs.teamDisbandModal;
      Alpine.store('modals').teamDisbandModalInitialized = true;
    }
  },

  async disbandTeam() {
    let response = await CTFd.pages.teams.disbandTeam();

    if (response.success) {
      window.location.reload();
    } else {
      this.errors = response.errors[""];
    }
  },

  openModal() {
    if (this.$refs.teamDisbandModal) {
      this.$refs.teamDisbandModal.style.display = 'block';
    }
  },

  closeModal() {
    if (this.$refs.teamDisbandModal) {
      this.$refs.teamDisbandModal.style.display = 'none';
    }
  },
}));

Alpine.data("CaptainMenu", () => ({
  editTeam() {
    const modal = Alpine.store('modals').teamEditModal;
    if (modal) {
      modal.style.display = 'block';
    }
  },

  chooseCaptain() {
    const modal = Alpine.store('modals').teamCaptainModal;
    if (modal) {
      modal.style.display = 'block';
    }
  },

  async inviteMembers() {
    const response = await CTFd.pages.teams.getInviteToken();

    if (response.success) {
      const code = response.data.code;
      const url = `${window.location.origin}${CTFd.config.urlRoot}/teams/invite?code=${code}`;

      document.querySelector("#team-invite-modal input[name=link]").value = url;
      this.$store.inviteToken = url;
      const modal = Alpine.store('modals').teamInviteModal;
      if (modal) {
        modal.style.display = 'block';
      }
    } else {
      Object.keys(response.errors).map(error => {
        const error_msg = response.errors[error];
        alert(error_msg);
      });
    }
  },

  disbandTeam() {
    const modal = Alpine.store('modals').teamDisbandModal;
    if (modal) {
      modal.style.display = 'block';
    }
  },
}));

Alpine.data("TeamGraphs", () => ({
  solves: null,
  fails: null,
  awards: null,
  solveCount: 0,
  failCount: 0,
  awardCount: 0,

  getSolvePercentage() {
    return ((this.solveCount / (this.solveCount + this.failCount)) * 100).toFixed(2);
  },

  getFailPercentage() {
    return ((this.failCount / (this.solveCount + this.failCount)) * 100).toFixed(2);
  },

  getCategoryBreakdown() {
    const categories = [];
    const breakdown = {};

    this.solves.data.map(solve => {
      categories.push(solve.challenge.category);
    });

    categories.forEach(category => {
      if (category in breakdown) {
        breakdown[category] += 1;
      } else {
        breakdown[category] = 1;
      }
    });

    const data = [];
    for (const property in breakdown) {
      data.push({
        name: property,
        count: breakdown[property],
        percent: (breakdown[property] / categories.length) * 100,
        color: colorHash(property),
      });
    }

    return data;
  },

  async init() {
    this.solves = await CTFd.pages.teams.teamSolves("me");
    this.fails = await CTFd.pages.teams.teamFails("me");
    this.awards = await CTFd.pages.teams.teamAwards("me");

    this.solveCount = this.solves.meta.count;
    this.failCount = this.fails.meta.count;
    this.awardCount = this.awards.meta.count;

    let optionMerge = window.teamScoreGraphChartOptions;

    embed(
      this.$refs.scoregraph,
      getUserScoreOption(
        CTFd.team.id,
        CTFd.team.name,
        this.solves.data,
        this.awards.data,
        optionMerge,
      ),
    );
  },
}));

Alpine.start();