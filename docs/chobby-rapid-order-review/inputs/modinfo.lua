return {
  name = 'BYAR Chobby',
  shortName = 'BYAR_CHOBBY',
  description = 'BYAR mutator for Chobby',
  version = 'test-4630-26b5200',
  mutator = 'Official',
  modtype = 5,
  onlyLocal = true,
  depend = {
      -- For developing base chobby, switch out dependency
      --'rapid://chobby:test', --this uses rapid pinned chobby
      --'Chobby test-4630-26b5200', -- this specifies chobby.sdd working path
  },

}
