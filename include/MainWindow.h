/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#ifndef SCAP_WORKBENCH_MAIN_WINDOW_H_
#define SCAP_WORKBENCH_MAIN_WINDOW_H_

#include "ForwardDecls.h"
#include "Scanner.h"

#include <QMainWindow>
#include <QThread>
#include <QMenu>

extern "C"
{
#include <xccdf_benchmark.h>
}

#include "ui_MainWindow.h"

/**
 * The central "singleton without global access" class representing
 * aplication's main window.
 */
class MainWindow : public QMainWindow
{
    Q_OBJECT

    public:
        MainWindow(QWidget* parent = 0);
        virtual ~MainWindow();

    public slots:
        /**
         * @brief Clears everything produced during the scan
         */
        void clearResults();

        /**
         * @brief Opens a specific file
         */
        void openFile(const QString& path);

        /**
         * @brief Opens a file dialog and makes user select a file or exit the app
         *
         * The file dialog keeps opening until a file is chosen or user
         * pressed Cancel.
         */
        void openFileDialog();

        /**
         * @brief Queues a file dialog to be opened later when in the event loop
         *
         * This avoids having a modal dialog block event queues.
         * @see MainWindow::openFileDialog
         */
        void openFileDialogAsync();

        /**
         * @brief Checks whether a file is currently opened
         */
        bool fileOpened() const;

        /**
         * @brief Automatically determines scanner mode based on checkbox state
         */
        void scanAsyncAutoMode();

        /**
         * @brief Starts scanning in a separate thread and returns
         *
         * @see MainWindow::cancelScanAsync()
         *
         * This method asserts that session has already been loaded
         * and that scanning is not running currently (in other words:
         * scanning has to end or be canceled before scanAsync can be
         * called again).
         */
        void scanAsync(ScannerMode scannerMode = SM_SCAN);

        /**
         * @note This will only work if scan results are still in ResultViewer.
         *
         * @see MainWindow::scanAndRemediateAsync
         */
        void offlineRemediateAsync();

        /**
         * @brief Cancels scanning in separate thread
         *
         * This method asserts that session has already been loaded.
         * It is not recommended but you can call this method even if scan
         * is not running at the time. The reason why this is handled is to
         * deal with scan finished/canceled race that could happen (at least in theory).
         */
        void cancelScanAsync();

    protected:
        /// reimplemented to make sure we cancel any scanning before closing the window
        virtual void closeEvent(QCloseEvent* event);

    private:
        /**
         * @brief Closes currently opened file (if any) and resets the interface
         *
         * If you want to make the editor close current file and make the
         * user open a new one, use MainWindow::openFileDialog, this method is
         * intended to be used internally.
         *
         * @see MainWindow::openFileDialog
         */
        void closeFile();

        /**
         * @brief Reloads the session, datastream split is potentially done again
         *
         * The main purpose of this method is to allow to reload the session when
         * parameters that affect "loading" of the session change. These parameters
         * are mainly datastream ID and component ID.
         */
        void reloadSession();

    public: // TailoringWindow calls this
        /**
         * @brief Refreshes items of the profile combobox with data from the session
         *
         * @note This method does attempt to "keep" the previous selection if possible.
         */
        void refreshProfiles();

    private:

        /**
         * @brief Destroys the scanning thread and associated data
         *
         * Also resets UI to a state where scanning is not running.
         */
        void cleanupScanThread();

        /// UI designed in Qt Designer
        Ui_MainWindow mUI;

        /// Qt Dialog that displays messages (errors, warnings, infos)
        /// Gets shown whenever a warning or error is emitted
        DiagnosticsDialog* mDiagnosticsDialog;

        /// Menu used for the tailor "combo pushbutton"
        QMenu* mSaveMenu;

        QAction* mSaveIntoDirAction;
        QAction* mSaveAsRPMAction;

        /// This is our central point of interaction with openscap
        ScanningSession* mScanningSession;

        /// Qt Dialog that displays results and allows user to save them
        ResultViewer* mResultViewer;

        /// Thread that handles scanning and/or remediating, NULL if none is underway
        QThread* mScanThread;
        /**
         * This is a scanner suitable for scanning target as specified by user
         * @see Scanner
         */
        Scanner* mScanner;

        /// Remembers old tailoring combobox ID in case we want to revert to it when user cancels
        int mOldTailoringComboBoxIdx;
        QVariant mLoadedTailoringFileUserData;

    signals:
        /**
         * @brief We signal this to show the dialog
         *
         * This is to make sure we open the dialog in the event loop, not 
         * before it even starts.
         */
        void showOpenFileDialog();

        /**
         * @brief This is signaled when scanning is canceled
         *
         * Qt handles thread messaging for us via the slot & signal mechanism.
         * The event loop of MainWindow runs in one thread, the event loop of
         * the scanner runs in another thread. Both are basically synchronisation
         * queues. This is why we emit this signal instead of calling scanner's
         * methods directly.
         *
         * Instead of emitting this signal directly, please use
         * MainWindow::cancelScanAsync()
         */
        void cancelScan();

    private slots:
        /// Checklist changed, we might have to reload session
        void checklistComboboxChanged(int index);
        /// Tailoring file changed, we might have to reload session
        void tailoringFileComboboxChanged(int index);
        /// Profile change, we simply change the profile id in the session
        void profileComboboxChanged(int index);

    public slots:
        /// Refreshes the selected rules tree according to current profile
        void refreshSelectedRulesTree();

    private slots:

        /**
         * @brief This slot gets triggered by the scanner to notify of a new result
         *
         * Used for progress estimation.
         */
        void scanProgressReport(const QString& rule_id, const QString& result);

        /**
         * @brief Scanner triggers this to show a message about progress
         *
         * Example: Connecting to remote target..., Copying input file..., etc.
         * No action is required by the user upon receiving this message.
         */
        void scanInfoMessage(const QString& message);

        /**
         * @brief Scanner triggers this to show a warning message
         *
         * Scanner must continue to scan after triggering this, the dialog
         * will be modal but scanning will continue in the background and
         * results will be visible. User can resume normal operation after
         * dismissing the warning dialog.
         */
        void scanWarningMessage(const QString& message);

        /**
         * @brief Scanner triggers this to show an error message
         *
         * Scanner might continue to scan after triggering this, the dialog
         * will be modal but scanning may continue in the background and
         * results will be visible.
         *
         * However scanner is expected to trigger scanCanceled after triggering
         * the error report.
         */
        void scanErrorMessage(const QString& message);

        /**
         * @brief Scanner triggers this after cancelation is complete
         *
         * @note It is most likely that user pressed the "Cancel" button to
         * trigger this but sometimes scanner will trigger cancelation when
         * unrecoverable errors are encountered.
         */
        void scanCanceled();

        /**
         * @brief Scanner triggers this after scan successfuly finishes
         */
        void scanFinished();

        /**
         * @brief When triggered, the ResultViewer is shown as a modal dialog
         *
         * Sole application control is passed to ResultViewer until user closes
         * it. It is not destroyed upon closing, just hidden.
         */
        void showResults();

        void inheritAndEditProfile(bool shadowed);

        void tailorNewID();
        void tailorShadowed();
        void editProfile();

        /**
         * @brief If current profile has been tailored, it gets edited, else it gets tailored with new ID
         *
         * The goal of this negotiation function is to make it easier to use
         * scap-workbench. It is one less thing to worry about and should be
         * what users need in 99% of cases.
         */
        void customizeProfile();

        void saveTailoring();

        void saveIntoDirectory();
        void saveAsRPM();

        void markUnsavedTailoringChanges();
        void markNoUnsavedTailoringChanges();
        void markLoadedTailoringFile(const QString& filePath);
        bool unsavedTailoringChanges() const;
};

#endif
